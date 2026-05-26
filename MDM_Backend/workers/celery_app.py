"""
signalmdm/workers/celery_app.py
---------------------------------
Celery application instance.

Usage:
    # Start worker (from MDM_Backend/ with venv activated):
    celery -A workers.celery_app worker --loglevel=info

    # Monitor with Flower:
    celery -A workers.celery_app flower
"""

from __future__ import annotations

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Use centralized Redis URL — single source of truth
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Note: Celery manages its own connections via kombu/amqp.
# The core.redis_client pool is used by the auth middleware + app code only.

celery = Celery(
    "signalmdm_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "workers.raw_worker",
        "workers.staging_worker",
    ],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,                  # Ack only after task completes
    worker_prefetch_multiplier=1,         # Fair task distribution
    task_soft_time_limit=300,             # 5 min soft limit
    task_time_limit=600,                  # 10 min hard limit
    result_expires=86400,                 # Results kept for 24 h
)
