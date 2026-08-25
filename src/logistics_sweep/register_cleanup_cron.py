import hashlib
import os

from .infrai_client import CronClient


def register_cleanup_cron() -> str:
    task_url = os.environ["CLEANUP_TASK_URL"]
    cron_expr = "15 2 * * *"
    schedule_key = hashlib.sha256(f"{cron_expr}\0{task_url}".encode()).hexdigest()
    cron = CronClient()
    result = cron.create(
        cron_expr=cron_expr,
        task=task_url,
        idempotency_key=f"stale-logistics-sweep-{schedule_key}",
    )
    return str(result["job_id"])


if __name__ == "__main__":
    print(f"Scheduled cleanup job: {register_cleanup_cron()}")
