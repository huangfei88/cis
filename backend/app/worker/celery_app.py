from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "cis_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # SECURITY: tasks are not retried automatically — execution is not idempotent
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
