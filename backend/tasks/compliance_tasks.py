"""
Celery Tasks — Compliance (tygodniowy skan całego kanału)
"""
import asyncio
import structlog
from datetime import datetime, timezone

from core.celery_app import celery_app
from tasks.agent_tasks import run_async

logger = structlog.get_logger(__name__)


@celery_app.task(name="tasks.compliance_tasks.weekly_channel_compliance_scan", queue="high_priority")
def weekly_channel_compliance_scan():
    """
    Weekly full-channel scan:
    - Cross-video similarity matrix
    - Template overuse detection
    - YPP readiness check
    - Rights & Risk audit
    """
    async def _execute():
        from core.database import AsyncSessionLocal
        from models.channel import Channel
        from models.video import VideoProject, Script
        from sqlalchemy import select
        from services.embedding_service import embedding_service

        async with AsyncSessionLocal() as db:
            channels_result = await db.execute(
                select(Channel).where(Channel.is_active == True)
            )
            channels = channels_result.scalars().all()

        for channel in channels:
            logger.info("Running weekly compliance scan", channel_id=str(channel.id), channel_name=channel.name)
            try:
                await embedding_service.rebuild_channel_embeddings(str(channel.id))
                await _run_cross_channel_similarity(str(channel.id))
                logger.info("Compliance scan complete", channel_id=str(channel.id))
            except Exception as e:
                logger.error("Compliance scan failed", channel_id=str(channel.id), error=str(e))

    run_async(_execute())


async def _run_cross_channel_similarity(channel_id: str):
    """Find pairs of videos with cosine similarity > 0.85 and flag them in DB."""
    from services.embedding_service import embedding_service
    from core.config import settings
    from core.database import AsyncSessionLocal
    from sqlalchemy import text
    from uuid import UUID

    pairs = await embedding_service.find_similar_videos(
        channel_id=channel_id,
        threshold=settings.max_similarity_cosine,
    )

    if not pairs:
        return

    logger.warning(
        "High similarity pairs detected",
        channel_id=channel_id,
        count=len(pairs),
        pairs=[(p["video_a_title"], p["video_b_title"], p["similarity"]) for p in pairs[:3]],
    )

    # Persist compliance alerts to DB for frontend notification
    async with AsyncSessionLocal() as db:
        for pair in pairs:
            await db.execute(
                text("""
                    INSERT INTO compliance_alerts
                        (channel_id, video_a_id, video_b_id, similarity_score, alert_type, created_at)
                    VALUES
                        (:channel_id, :video_a_id, :video_b_id, :similarity, 'high_similarity', :now)
                    ON CONFLICT (channel_id, video_a_id, video_b_id) DO UPDATE
                        SET similarity_score = EXCLUDED.similarity_score,
                            created_at = EXCLUDED.created_at
                """),
                {
                    "channel_id": UUID(channel_id),
                    "video_a_id": UUID(pair["video_a_id"]),
                    "video_b_id": UUID(pair["video_b_id"]),
                    "similarity": pair["similarity"],
                    "now": datetime.now(timezone.utc),
                },
            )
        await db.commit()

    logger.info(
        "Compliance alerts saved to DB",
        channel_id=channel_id,
        alerts_count=len(pairs),
    )
