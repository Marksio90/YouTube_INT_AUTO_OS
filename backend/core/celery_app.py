"""
Celery Application — YouTube Intelligence & Automation OS
Background task processor dla pipeline agentów AI.
"""
from celery import Celery
from celery.signals import worker_ready, task_prerun, task_postrun, task_failure
from kombu import Queue
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)

# ============================================================
# Celery App Configuration
# ============================================================

celery_app = Celery(
    "ytautos",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.agent_tasks",
        "tasks.video_tasks",
        "tasks.analytics_tasks",
        "tasks.compliance_tasks",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing — dedicated queues per priority
    task_queues=(
        Queue("high_priority"),       # compliance, pre-publish checks
        Queue("default"),             # script generation, thumbnails
        Queue("low_priority"),        # analytics, post-publish review
        Queue("video_rendering"),     # FFmpeg — heavy CPU tasks
    ),
    task_default_queue="default",

    # Task routing rules
    task_routes={
        "tasks.compliance_tasks.*": {"queue": "high_priority"},
        "tasks.agent_tasks.run_originality_check": {"queue": "high_priority"},
        "tasks.video_tasks.assemble_video": {"queue": "video_rendering"},
        "tasks.analytics_tasks.*": {"queue": "low_priority"},
    },

    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    task_default_retry_delay=30,

    # Result expiry (24h)
    result_expires=86400,

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Post-publish review checkpoints (2h, 24h, 72h, 7d, 28d)
        "post-publish-2h-check": {
            "task": "tasks.analytics_tasks.post_publish_review",
            "schedule": 7200.0,  # every 2 hours
            "args": ("2h",),
        },
        "post-publish-24h-check": {
            "task": "tasks.analytics_tasks.post_publish_review",
            "schedule": 86400.0,
            "args": ("24h",),
        },
        # Channel health monitoring (every hour)
        "channel-health-monitor": {
            "task": "tasks.analytics_tasks.monitor_channel_health",
            "schedule": 3600.0,
        },
        # Weekly compliance scan
        "weekly-compliance-scan": {
            "task": "tasks.compliance_tasks.weekly_channel_compliance_scan",
            "schedule": 604800.0,
        },
    },
)


# ============================================================
# Signals for monitoring
# ============================================================

@worker_ready.connect
def on_worker_ready(**kwargs):
    logger.info("Celery worker ready", queues=["high_priority", "default", "low_priority", "video_rendering"])


@task_prerun.connect
def on_task_start(task_id, task, args, kwargs, **extras):
    logger.info("Task started", task_id=task_id, task_name=task.name)


@task_postrun.connect
def on_task_done(task_id, task, args, kwargs, retval, state, **extras):
    logger.info("Task completed", task_id=task_id, task_name=task.name, state=state)


@task_failure.connect
def on_task_failure(task_id, exception, traceback, **kwargs):
    logger.error("Task failed", task_id=task_id, error=str(exception))
