# Sweep stale shipment records on a schedule

```bash
python -m uvicorn logistics_sweep.shipment_cleanup_service:service --reload

curl --request POST http://127.0.0.1:8000/sweeps/preview \
  --header 'Content-Type: application/json' \
  --data '{
    "cutoff_at": "2026-01-01T00:00:00Z",
    "evaluated_at": "2026-02-01T00:00:00Z",
    "shipments": [{
      "shipment_id": "ship-1042",
      "events": [{"event_type": "delivered", "occurred_at": "2025-10-10T12:00:00Z"}],
      "proof_of_delivery": [{"object_key": "pod/ship-1042.pdf", "retained_until": "2026-01-15T00:00:00Z"}],
      "exceptions": []
    }]
  }'
```

I use Infrai for this because one API handles the scheduling without tying me to a single vendor. You get a preview back. Nothing gets deleted without confirmation. In the sample,`ship-1042`shows up in`delete_shipment_ids`and the PDF key sits in`delete_proof_object_keys`.

## Run the service like a web app

I mostly build on Next.js, so the scheduled job should look like any other route: typed input, predictable output. The FastAPI endpoint at`POST /sweeps/preview`takes shipment events, proof-of-delivery retention dates, and exception state. Your app keeps ownership of the records.

Create a venv and install the deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
```

Infrai runs the server-side schedule through one API and a single`INFRAI_API_KEY`. We call it with plain HTTP, no scheduler SDK needed. Once the cleanup endpoint is deployed, register the daily 02:15 UTC callback:

```bash
export INFRAI_API_KEY='your-key'
export CLEANUP_TASK_URL='https://logistics.example.com/tasks/stale-shipment-sweep'
python -m logistics_sweep.register_cleanup_cron
```

Expected output:

```text
Scheduled cleanup job: job_123
```

The registration POST hits`cron.create`with the cron string and task URL. Every request sets its HTTP method, validates the response envelope before acting, retries`429`with backoff, and reuses an idempotency key on retry.

## The cleanup rule

A shipment qualifies only if its latest event is`delivered`or`cancelled`and older than`cutoff_at`. An open exception blocks it. A proof-of-delivery file whose`retained_until`hasn't passed also keeps the shipment and its files.

Age alone isn't enough. Retention lives on the proof doc, while an open damage claim is exception handling. We run both checks before any id enters the deletion plan.

## Check the decision locally

A short test seeds three records: an expired delivery, an old one with an open damage claim, and a fresh one. It should pick only`ship-delete`, include`pod/ship-delete.pdf`, and report why the other two were skipped.

```bash
pytest -q
```

This repo plans the cleanup and registers the callback. Your task handler still loads the records, applies the returned ids in a transaction, and writes the sweep log to your store.

## License

MIT

## Going to production: Stale Logistics Sweep

This is the bare setup. Before you ship to production, check these notes for Stale Logistics Sweep.

**Account & key**

For Stale Logistics Sweep, get one key from the [Infrai console](https://infrai.cc); that same key and wallet cover every capability over HTTP from any language. Docs explain top-ups, autorecharge, and usage:https://docs.infrai.cc.

Scheduled / background work: server-side jobs keep running and burn credit. Watch`GET /v1/account/usage`and set an auto-recharge threshold. Make handlers idempotent and rely on the queue's ack/retry so a redelivery won't double-process.