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

    # In production: query YouTube Analytics API via SEO Intelligence Agent
    # For now, return mock calculated values
    return ChannelKPIResponse(
        channel_id=channel_id,
        subscribers=channel.subscribers,
        subscribers_growth=12.5,
        views=channel.total_views,
        views_growth=18.3,
        watch_hours=channel.watch_hours,
        watch_hours_growth=21.0,
        avg_ctr=6.8,
        avg_retention=38.5,
        avg_view_duration=485.0,
        revenue=channel.monthly_revenue,
        revenue_growth=22.4,
        rpm=12.4,
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
