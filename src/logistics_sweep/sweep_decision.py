from .cleanup_models import CleanupSweepRequest, CleanupSweepResult, SkippedShipment


def plan_cleanup(request: CleanupSweepRequest) -> CleanupSweepResult:
    shipment_ids: list[str] = []
    proof_keys: list[str] = []
    skipped: list[SkippedShipment] = []

    for shipment in request.shipments:
        latest_event = max(shipment.events, key=lambda event: event.occurred_at)

        if latest_event.event_type not in {"delivered", "cancelled"} or latest_event.occurred_at >= request.cutoff_at:
            skipped.append(SkippedShipment(shipment_id=shipment.shipment_id, reason="active_shipment"))
            continue
        if any(item.resolved_at is None for item in shipment.exceptions):
            skipped.append(SkippedShipment(shipment_id=shipment.shipment_id, reason="open_exception"))
            continue
        if any(item.retained_until >= request.evaluated_at for item in shipment.proof_of_delivery):
            skipped.append(SkippedShipment(shipment_id=shipment.shipment_id, reason="retained_proof"))
            continue

        shipment_ids.append(shipment.shipment_id)
        proof_keys.extend(item.object_key for item in shipment.proof_of_delivery)

    return CleanupSweepResult(
        delete_shipment_ids=shipment_ids,
        delete_proof_object_keys=proof_keys,
        skipped=skipped,
    )
