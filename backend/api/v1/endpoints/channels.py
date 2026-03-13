from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import uuid
import re

from core.database import get_db
from core.auth import get_current_user, require_creator
from models.user import User
from models.channel import Channel
from schemas.channel import ChannelCreate, ChannelUpdate, ChannelResponse, ChannelKPIResponse


async def _fetch_channel_kpis(channel, period: str) -> dict:
    """
    Fetch real KPI data from YouTube Analytics API using stored OAuth tokens.
    Falls back to zeros if channel is not OAuth-authorized or API is unavailable.
    """
    _PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
    days = _PERIOD_DAYS.get(period, 30)

    if not channel.youtube_channel_id:
        return _zero_kpis()

    try:
        from services.youtube_oauth_service import youtube_oauth_service
        from services.youtube_service import youtube_service
        from datetime import date, timedelta

        access_token = await youtube_oauth_service.get_valid_access_token(str(channel.id))
        if not access_token:
            return _zero_kpis()

        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)

        current = await youtube_service.get_channel_analytics(
            channel_id=channel.youtube_channel_id,
            access_token=access_token,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        previous = await youtube_service.get_channel_analytics(
            channel_id=channel.youtube_channel_id,
            access_token=access_token,
            start_date=prev_start.isoformat(),
            end_date=start_date.isoformat(),
        )

        def _pct_change(curr, prev):
            if not prev:
                return 0.0
            return round((curr - prev) / prev * 100, 1)

        return {
            "subscribers_growth": _pct_change(
                current.get("subscribersGained", 0), previous.get("subscribersGained", 0)
            ),
            "views_growth": _pct_change(current.get("views", 0), previous.get("views", 0)),
            "watch_hours_growth": _pct_change(
                current.get("estimatedMinutesWatched", 0),
                previous.get("estimatedMinutesWatched", 0),
            ),
            "avg_ctr": round(current.get("annotationClickThroughRate", 0) * 100, 2),
            "avg_retention": round(current.get("averageViewPercentage", 0), 1),
            "avg_view_duration": round(current.get("averageViewDuration", 0), 0),
            "revenue_growth": _pct_change(
                current.get("estimatedRevenue", 0), previous.get("estimatedRevenue", 0)
            ),
            "rpm": round(current.get("estimatedRevenue", 0) / max(current.get("views", 1), 1) * 1000, 2),
        }
    except Exception:
        return _zero_kpis()


def _zero_kpis() -> dict:
    return {
        "subscribers_growth": 0.0,
        "views_growth": 0.0,
        "watch_hours_growth": 0.0,
        "avg_ctr": 0.0,
        "avg_retention": 0.0,
        "avg_view_duration": 0.0,
        "revenue_growth": 0.0,
        "rpm": 0.0,
    }


router = APIRouter(prefix="/channels", tags=["channels"])


def slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug[:100]


@router.get("", response_model=List[ChannelResponse])
async def list_channels(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Channel)
    if is_active is not None:
        query = query.where(Channel.is_active == is_active)
    query = query.order_by(Channel.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(
    data: ChannelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    slug = slugify(data.name)
    # Ensure unique slug
    existing = await db.execute(select(Channel).where(Channel.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    channel = Channel(
        slug=slug,
        **data.model_dump(),
    )
    db.add(channel)
    await db.flush()
    await db.refresh(channel)
    return channel


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: uuid.UUID,
    data: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(channel, field, value)

    await db.flush()
    await db.refresh(channel)
    return channel


@router.get("/{channel_id}/kpis", response_model=ChannelKPIResponse)
async def get_channel_kpis(
    channel_id: uuid.UUID,
    period: str = Query("30d", pattern="^(7d|30d|90d|365d)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Fetch real analytics from YouTube Analytics API if OAuth tokens available
    analytics_data = await _fetch_channel_kpis(channel, period)
    return ChannelKPIResponse(
        channel_id=channel_id,
        subscribers=channel.subscribers,
        subscribers_growth=analytics_data["subscribers_growth"],
        views=channel.total_views,
        views_growth=analytics_data["views_growth"],
        watch_hours=channel.watch_hours,
        watch_hours_growth=analytics_data["watch_hours_growth"],
        avg_ctr=analytics_data["avg_ctr"],
        avg_retention=analytics_data["avg_retention"],
        avg_view_duration=analytics_data["avg_view_duration"],
        revenue=channel.monthly_revenue,
        revenue_growth=analytics_data["revenue_growth"],
        rpm=analytics_data["rpm"],
        period=period,
    )


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    channel.is_active = False
    await db.flush()
