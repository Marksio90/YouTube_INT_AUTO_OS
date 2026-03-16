from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_db
from core.auth import get_current_user, require_creator
from models.user import User
from models.video import VideoProject, PipelineStage, ComplianceReport, VideoAnalytics
from models.agent import AgentRun, AgentStatus
from schemas.video import (
    VideoProjectCreate, VideoProjectUpdate, VideoProjectResponse,
    ComplianceReportResponse,
)
from pydantic import BaseModel


class StageAdvanceRequest(BaseModel):
    stage: str

router = APIRouter(prefix="/videos", tags=["videos"])

# Pipeline stage progression order
STAGE_ORDER = [s.value for s in PipelineStage]


@router.get("", response_model=List[VideoProjectResponse])
async def list_videos(
    channel_id: Optional[uuid.UUID] = Query(None),
    stage: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(VideoProject)
    if channel_id:
        query = query.where(VideoProject.channel_id == channel_id)
    if stage:
        query = query.where(VideoProject.stage == stage)
    query = query.order_by(VideoProject.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=VideoProjectResponse, status_code=201)
async def create_video(
    data: VideoProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    video = VideoProject(**data.model_dump())
    db.add(video)
    await db.flush()
    await db.refresh(video)
    return video


@router.get("/{video_id}", response_model=VideoProjectResponse)
async def get_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")
    return video


@router.patch("/{video_id}", response_model=VideoProjectResponse)
async def update_video(
    video_id: uuid.UUID,
    data: VideoProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")

    ALLOWED_UPDATE_FIELDS = {"title", "stage", "target_keywords", "scheduled_for"}
    updates = {
        k: v for k, v in data.model_dump(exclude_none=True).items()
        if k in ALLOWED_UPDATE_FIELDS
    }

    if "stage" in updates and updates["stage"] not in STAGE_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {updates['stage']}")

    for field, value in updates.items():
        setattr(video, field, value)

    await db.flush()
    await db.refresh(video)
    return video


@router.patch("/{video_id}/stage", response_model=VideoProjectResponse)
async def advance_video_stage(
    video_id: uuid.UUID,
    stage_data: StageAdvanceRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")

    new_stage = stage_data.stage
    if new_stage not in STAGE_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {new_stage}")

    if new_stage == "review":
        if video.originality_score and video.originality_score < 85:
            raise HTTPException(
                status_code=422,
                detail=f"Quality gate failed: Originality score {video.originality_score} < 85"
            )

    video.stage = new_stage
    await db.flush()
    await db.refresh(video)
    return video


@router.get("/{video_id}/compliance", response_model=ComplianceReportResponse)
async def get_compliance_report(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ComplianceReport).where(ComplianceReport.video_project_id == video_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Compliance report not found. Run compliance check first.")
    return report


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")
    await db.delete(video)
    await db.flush()


@router.get("/{video_id}/analytics")
async def get_video_analytics(
    video_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(VideoAnalytics)
        .where(VideoAnalytics.video_project_id == video_id)
        .order_by(VideoAnalytics.created_at.desc())
    )
    analytics = result.scalars().all()
    if not analytics:
        raise HTTPException(status_code=404, detail="No analytics found for this video")
    latest = analytics[0]
    return {
        "videoId": str(latest.video_project_id),
        "views": latest.views,
        "watchTimeMinutes": latest.watch_time_minutes,
        "avgViewDurationSeconds": latest.avg_view_duration_seconds,
        "avgRetentionPercent": latest.avg_retention_percent,
        "ctr": latest.ctr,
        "likes": latest.likes,
        "comments": latest.comments,
        "shares": latest.shares,
        "revenue": latest.revenue,
        "rpm": latest.rpm,
        "retentionCurve": latest.retention_curve or [],
        "trafficSources": latest.traffic_sources or [],
    }


@router.post("/{video_id}/compliance/run", status_code=202)
async def run_compliance_check(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """Trigger Originality & Transformation Agent + Rights & Risk Agent."""
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")

    run = AgentRun(
        agent_id="originality_transformation",
        video_project_id=video_id,
        channel_id=video.channel_id,
        status=AgentStatus.running,
        input_data={"video_project_id": str(video_id), "channel_id": str(video.channel_id)},
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    from api.v1.endpoints.agents import _execute_agent_background
    background_tasks.add_task(
        _execute_agent_background,
        str(run.id),
        "originality_transformation",
        run.input_data,
    )

    return {
        "message": "Compliance check queued",
        "video_id": str(video_id),
        "run_id": str(run.id),
        "stream_url": f"/api/v1/agents/runs/{run.id}/stream",
    }
