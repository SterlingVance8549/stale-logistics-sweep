from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ShipmentEvent(BaseModel):
    event_type: Literal["created", "in_transit", "delivered", "cancelled"]
    occurred_at: datetime


class ProofOfDelivery(BaseModel):
    object_key: str
    retained_until: datetime


class ShipmentException(BaseModel):
    reason: str
    resolved_at: datetime | None = None


class ShipmentRecord(BaseModel):
    shipment_id: str
    events: list[ShipmentEvent] = Field(min_length=1)
    proof_of_delivery: list[ProofOfDelivery] = Field(default_factory=list)
    exceptions: list[ShipmentException] = Field(default_factory=list)


class CleanupSweepRequest(BaseModel):
    cutoff_at: datetime
    evaluated_at: datetime
    shipments: list[ShipmentRecord]


class SkippedShipment(BaseModel):
    shipment_id: str
    reason: Literal["active_shipment", "retained_proof", "open_exception"]


class CleanupSweepResult(BaseModel):
    delete_shipment_ids: list[str]
    delete_proof_object_keys: list[str]
    skipped: list[SkippedShipment]
