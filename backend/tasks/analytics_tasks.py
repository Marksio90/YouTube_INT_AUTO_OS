"""
Celery Tasks — Analytics & Post-Publish Review
Automatyczne checkpointy: 2h, 24h, 72h, 7d, 28d po publikacji.
"""
from datetime import datetime, timezone, timedelta
import asyncio
import structlog

from core.celery_app import celery_app
from tasks.agent_tasks import run_async

logger = structlog.get_logger(__name__)


@celery_app.task(name="tasks.analytics_tasks.post_publish_review", queue="low_priority")
def post_publish_review(checkpoint: str):
    """
    Runs after publication at: 2h, 24h, 72h, 7d, 28d.
    Fetches YouTube Analytics data and triggers Watch-Time Forensics.
    """
    async def _execute():
        from core.database import AsyncSessionLocal
        from models.video import VideoProject, PipelineStage
        from sqlalchemy import select
        from services.youtube_service import youtube_service

        checkpoint_hours = {"2h": 2, "24h": 24, "72h": 72, "7d": 168, "28d": 672}
        hours = checkpoint_hours.get(checkpoint, 2)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours + 1)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(VideoProject).where(
                    VideoProject.stage == PipelineStage.published,
                    VideoProject.published_at >= cutoff,
                    VideoProject.published_at <= datetime.now(timezone.utc) - timedelta(hours=hours - 0.5),
                )
            )
            videos = result.scalars().all()

        for video in videos:
            if video.published_url:
                try:
                    # Fetch fresh analytics from YouTube
                    await youtube_service.sync_video_analytics(
                        str(video.id), video.published_url, str(video.channel_id)
                    )
                    logger.info("Analytics synced", video_id=str(video.id), checkpoint=checkpoint)
                except Exception as e:
                    logger.warning("Analytics sync failed", video_id=str(video.id), error=str(e))

    run_async(_execute())


@celery_app.task(name="tasks.analytics_tasks.monitor_channel_health", queue="low_priority")
def monitor_channel_health():
    """Hourly channel health check — detect CTR drops, shadow banning signals."""
    async def _execute():
        from core.database import AsyncSessionLocal
        from models.channel import Channel
        from sqlalchemy import select
        from services.youtube_service import youtube_service

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Channel).where(Channel.is_active == True)
            )
            channels = result.scalars().all()

        for channel in channels:
            if channel.youtube_channel_id:
                try:
                    await youtube_service.sync_channel_metrics(
                        str(channel.id),
                        channel.youtube_channel_id
                    )
                except Exception as e:
                    logger.warning("Channel sync failed", channel_id=str(channel.id), error=str(e))

    run_async(_execute())
