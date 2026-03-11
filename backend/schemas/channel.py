from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    niche: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    youtube_channel_id: Optional[str] = None
    content_pillars: List[str] = Field(default_factory=list)
    thumbnail_style: Optional[str] = None


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    description: Optional[str] = None
    content_pillars: Optional[List[str]] = None
    thumbnail_style: Optional[str] = None


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    niche: str
    description: Optional[str]
    youtube_channel_id: Optional[str]
    subscribers: int
    total_views: int
    watch_hours: float
    monthly_revenue: float
    ypp_status: str
    compliance_score: float
    originality_score: float
    brand_consistency_score: float
    content_pillars: List[str]
    thumbnail_style: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ChannelKPIResponse(BaseModel):
    channel_id: UUID
    subscribers: int
    subscribers_growth: float
    views: int
    views_growth: float
    watch_hours: float
    watch_hours_growth: float
    avg_ctr: float
    avg_retention: float
    avg_view_duration: float
    revenue: float
    revenue_growth: float
    rpm: float
    period: str
