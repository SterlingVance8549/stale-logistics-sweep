from logistics_sweep.cleanup_models import CleanupSweepRequest
from logistics_sweep.sweep_decision import plan_cleanup


def test_sweep_deletes_only_expired_closed_shipments() -> None:
    request = CleanupSweepRequest.model_validate(
        {
            "cutoff_at": "2026-01-01T00:00:00Z",
            "evaluated_at": "2026-02-01T00:00:00Z",
            "shipments": [
                {
                    "shipment_id": "ship-delete",
                    "events": [{"event_type": "delivered", "occurred_at": "2025-10-10T12:00:00Z"}],
                    "proof_of_delivery": [
                        {"object_key": "pod/ship-delete.pdf", "retained_until": "2026-01-15T00:00:00Z"}
                    ],
                    "exceptions": [{"reason": "address review", "resolved_at": "2025-10-11T00:00:00Z"}],
                },
                {
                    "shipment_id": "ship-hold",
                    "events": [{"event_type": "delivered", "occurred_at": "2025-09-01T00:00:00Z"}],
                    "exceptions": [{"reason": "damage claim", "resolved_at": None}],
                },
                {
                    "shipment_id": "ship-recent",
                    "events": [{"event_type": "delivered", "occurred_at": "2026-01-20T00:00:00Z"}],
                },
            ],
        }
    )

    result = plan_cleanup(request)

    assert result.delete_shipment_ids == ["ship-delete"]
    assert result.delete_proof_object_keys == ["pod/ship-delete.pdf"]
    assert [(item.shipment_id, item.reason) for item in result.skipped] == [
        ("ship-hold", "open_exception"),
        ("ship-recent", "active_shipment"),
    ]
