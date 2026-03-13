from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.auth import get_current_user
from models.user import User
from models.channel import Channel
from models.video import VideoProject

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get high-level portfolio overview for main dashboard."""
    # Channel stats
    channels_result = await db.execute(
        select(
            func.count(Channel.id).label("total_channels"),
            func.sum(Channel.subscribers).label("total_subscribers"),
            func.sum(Channel.total_views).label("total_views"),
            func.sum(Channel.watch_hours).label("total_watch_hours"),
            func.sum(Channel.monthly_revenue).label("total_monthly_revenue"),
        ).where(Channel.is_active == True)
    )
    channel_stats = channels_result.one()

    # Pipeline stats
    pipeline_result = await db.execute(
        select(VideoProject.stage, func.count(VideoProject.id).label("count"))
        .group_by(VideoProject.stage)
    )
    pipeline_stats = {row.stage: row.count for row in pipeline_result}

    return {
        "portfolio": {
            "total_channels": channel_stats.total_channels or 0,
            "total_subscribers": channel_stats.total_subscribers or 0,
            "total_views": channel_stats.total_views or 0,
            "total_watch_hours": channel_stats.total_watch_hours or 0.0,
            "total_monthly_revenue": channel_stats.total_monthly_revenue or 0.0,
        },
        "pipeline": pipeline_stats,
        "ypp_status": {
            "channels_active": 2,
            "channels_pending": 1,
            "channels_not_eligible": 0,
        },
    }


@router.get("/alerts")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current compliance, performance, and milestone alerts."""
    # In production: query from alerts table populated by agent background jobs
    return {
        "alerts": [
            {
                "type": "warning",
                "category": "compliance",
                "message": 'Video "5 Sekretow Inwestowania" ma similarity score 0.87 — ryzyko inauthentic content',
                "time": "2h temu",
                "action_url": "/compliance",
            },
            {
                "type": "info",
                "category": "milestone",
                "message": "Kanal AI Finanse PL: 4,821/5,000 subskrybentow — YPP upgrade w zasiegu",
                "time": "4h temu",
                "action_url": "/compliance",
            },
            {
                "type": "success",
                "category": "experiment",
                "message": 'Eksperyment A/B miniatur dla "ChatGPT vs Claude" zakonczony — wariant B +34% CTR',
                "time": "6h temu",
                "action_url": "/experiment-hub",
            },
        ],
        "total_unread": 3,
    }
