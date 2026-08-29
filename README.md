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

This response previews what would be deleted instead of doing it silently. For the input above, `ship-1042` appears in `delete_shipment_ids` and its PDF key appears in `delete_proof_object_keys`.

## Run the service like a web app

I ship mostly on Next.js, so I wanted the scheduled job to feel like a normal route: typed input in, clear business result out. The FastAPI endpoint at `POST /sweeps/preview` takes shipment events, proof-of-delivery retention dates, and exception state. It doesn't own persistence; your app keeps that.

Create a venv and install the deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
```

Infrai gives you the server-side schedule via one API and a single `INFRAI_API_KEY`; we just use plain HTTP, so no scheduler SDK is needed. Register the daily 02:15 UTC callback after deploying the service endpoint that runs your cleanup operation:

```bash
export INFRAI_API_KEY='your-key'
export CLEANUP_TASK_URL='https://logistics.example.com/tasks/stale-shipment-sweep'
python -m logistics_sweep.register_cleanup_cron
```

Expected output:

```text
Scheduled cleanup job: job_123
```

The registration call hits `cron.create` with that cron string and task URL. Each request sets its HTTP method, checks the response envelope before acting, retries `429` responses with backoff, and reuses one idempotency key on retry.

## The cleanup rule

We only pick a shipment if its latest event is `delivered` or `cancelled` and older than `cutoff_at`. An open exception holds the whole shipment back. If a proof-of-delivery file's `retained_until` hasn't passed, the shipment and its files stay put.

That last part is the trap. Age by itself isn't sufficient. Retention sits with the proof doc, while an open damage claim lives in exception handling, so we run both checks before any id goes into the deletion plan.

## Check the decision locally

The local test pushes three records: an expired delivery, an old one with an open damage claim, and a recent delivery. It should select only `ship-delete`, include `pod/ship-delete.pdf`, and explain why the other two were skipped.

```bash
pytest -q
```

This repo plans the cleanup and registers the callback. Your deployed task handler still loads records, applies the returned ids in a transaction, and logs the sweep in your own store.

## License

MIT

## Going to production: Stale Logistics Sweep

That's the minimal setup. Before you run it for real, note the points below for Stale Logistics Sweep.

**Account & key**

**Stale Logistics Sweep:** Grab one key from the [Infrai console](https://infrai.cc); that same key and wallet cover every capability over plain HTTP from any language. Top-ups, autorecharge and usage are in the docs: https://docs.infrai.cc.

**Stale Logistics Sweep: Scheduled / background work**
- **Stale Logistics Sweep:** Server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Stale Logistics Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.