"""Celery application instance for Germinal background workers."""

from __future__ import annotations

from celery import Celery

from src.settings import Settings

settings = Settings()

celery_app = Celery(
    "germinal",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["api.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # one task at a time per worker (Lean is CPU-heavy)
    result_expires=3600 * 24,  # keep results for 24 hours
)
