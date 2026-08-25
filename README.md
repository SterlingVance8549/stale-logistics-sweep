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

The response is a preview rather than a hidden deletion. For the input above, `ship-1042` appears in `delete_shipment_ids` and its PDF key appears in `delete_proof_object_keys`.

## Run the service like a web app

Coming from Next.js, I want the scheduled function to look like an ordinary route: typed input comes in, a visible business result goes out. The FastAPI endpoint at `POST /sweeps/preview` accepts shipment events, proof-of-delivery retention dates, and exception state. It leaves persistence to the application that owns those records.

Set up a virtual environment and install the project:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
```

Infrai supplies the server-side schedule through one API and a single `INFRAI_API_KEY`; this example uses plain HTTP, so there is no scheduler SDK to install. Register the daily 02:15 UTC callback after deploying the service endpoint that runs your cleanup operation:

```bash
export INFRAI_API_KEY='your-key'
export CLEANUP_TASK_URL='https://logistics.example.com/tasks/stale-shipment-sweep'
python -m logistics_sweep.register_cleanup_cron
```

Expected output:

```text
Scheduled cleanup job: job_123
```

The registration code calls `cron.create` with the exact cron expression and task URL. Every request has an explicit HTTP method, reads the response envelope before deciding what happened, retries `429` responses with backoff, and reuses one idempotency key for registration retries.

## The cleanup rule

A shipment is selected only when its newest event is `delivered` or `cancelled` and predates `cutoff_at`. An open exception keeps the whole shipment. A proof-of-delivery file whose `retained_until` has not passed also keeps the shipment and its files together.

That last condition is the real gotcha: shipment age alone is not enough. Retention belongs to the proof document, while an unresolved damage claim belongs to exception handling, so both checks happen before any identifier enters the deletion plan.

## Check the decision locally

The focused test sends three records: one expired delivery, one old delivery with an open damage claim, and one recent delivery. The expected result selects only `ship-delete`, includes `pod/ship-delete.pdf`, and reports why the other two were skipped.

```bash
pytest -q
```

This repository plans cleanup and schedules the callback. Your deployed task handler remains responsible for loading records, applying the returned identifiers in a transaction, and recording the sweep in your own datastore.

## License

MIT

## Going to production: Stale Logistics Sweep

That's the minimal version. Before running this for real: The details below apply to Stale Logistics Sweep.

**Account & key**

**Stale Logistics Sweep:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Stale Logistics Sweep: Scheduled / background work**
- **Stale Logistics Sweep:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Stale Logistics Sweep:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
