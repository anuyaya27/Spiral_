from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "mixedsignals",
    broker=settings.get_celery_broker_url(),
    backend=settings.get_celery_result_backend(),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "retention-cleanup-daily": {
        "task": "app.workers.tasks.retention_cleanup_job",
        "schedule": crontab(hour=2, minute=0),
    }
}

