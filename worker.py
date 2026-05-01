from config import Redisconfig
from celery import Celery
import os

celery_app = Celery(
    "tasks",
    broker=Redisconfig.REDIS_URL,
    backend=Redisconfig.REDIS_URL,
    include=["tasks"]
)

# Optional configuration
celery_app.conf.update(
    result_backend=Redisconfig.REDIS_URL,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max
)
