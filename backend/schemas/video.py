from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class VideoProjectCreate(BaseModel):
    channel_id: UUID
    title: str = Field(..., min_length=5, max_length=500)
    format: str = "long_form"
    niche: Optional[str] = None
    target_keywords: List[str] = Field(default_factory=list)
    estimated_duration_seconds: Optional[int] = None


class VideoProjectUpdate(BaseModel):
    title: Optional[str] = None
    stage: Optional[str] = None
    target_keywords: Optional[List[str]] = None
    scheduled_for: Optional[datetime] = None


class VideoProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    title: str
    stage: str
    format: str
    niche: Optional[str]
    target_keywords: List[str]
    hook_score: Optional[float]
    originality_score: Optional[float]
    thumbnail_score: Optional[float]
    seo_score: Optional[float]
    overall_quality_score: Optional[float]
    compliance_risk: Optional[str]
    assigned_agents: List[str]
    voice_track_url: Optional[str]
    thumbnail_urls: List[str]
    video_url: Optional[str]
    published_url: Optional[str]
    scheduled_for: Optional[datetime]
    published_at: Optional[datetime]
    estimated_duration_seconds: Optional[int]
    created_at: datetime
    updated_at: datetime


class ScriptCreate(BaseModel):
    video_project_id: UUID
    title: str
    hook: str
    intro: str
    problem: str
    deepening: str
    value: str
    cta: str


class ScriptGenerateRequest(BaseModel):
    video_project_id: UUID
    topic: str
    target_keywords: List[str] = Field(default_factory=list)
    target_duration_minutes: int = Field(default=12, ge=3, le=60)
    tone: str = "authoritative"
    hook_type: Optional[str] = None


class ScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_project_id: Optional[UUID]
    title: Optional[str]
    hook: Optional[str]
    intro: Optional[str]
    problem: Optional[str]
    deepening: Optional[str]
    value: Optional[str]
    cta: Optional[str]
    full_text: Optional[str]
    word_count: Optional[int]
    estimated_duration_seconds: Optional[int]
    hook_score: Optional[float]
    retention_score: Optional[float]
    naturality_score: Optional[float]
    originality_score: Optional[float]
    hook_variants: List[Dict[str, Any]]
    version: int
    created_at: datetime


class ComplianceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_project_id: UUID
    originality_score: float
    similarity_to_other_videos: float
    template_overuse_risk: str
    copyright_risk: str
    ai_disclosure_required: bool
    ai_disclosure_set: bool
    sponsor_disclosure_required: bool
    sponsor_disclosure_set: bool
    ypp_safe: bool
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    created_at: datetime
