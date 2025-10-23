from celery import Celery

from src.core.config import settings
from src.core.logger import log

celery_app = Celery(
    "speaker_diarization",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.task_timeout_minutes * 60,
    task_soft_time_limit=(settings.task_timeout_minutes - 5) * 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_default_queue="diarization",
    task_default_exchange="diarization",
    task_default_routing_key="diarization",
)

log.info("Celery app configured")