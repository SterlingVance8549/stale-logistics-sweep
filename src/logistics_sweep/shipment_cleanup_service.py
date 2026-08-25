from fastapi import FastAPI

from .cleanup_models import CleanupSweepRequest, CleanupSweepResult
from .sweep_decision import plan_cleanup

service = FastAPI(title="Shipment cleanup sweep")


@service.post("/sweeps/preview", response_model=CleanupSweepResult)
def preview_sweep(request: CleanupSweepRequest) -> CleanupSweepResult:
    return plan_cleanup(request)
