"""Weekly local-time scheduler; run exactly one Beat instance."""

import os

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()
app = Celery(
    "profile_updates",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    include=["src.app.workers.profile_updates"],
)
app.conf.update(
    timezone="Africa/Cairo",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="profile_updates",
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "weekly-profile-updates": {
            "task": "profiles.dispatch",
            "schedule": crontab(minute=0, hour=3, day_of_week="sun"),
        }
    },
)
