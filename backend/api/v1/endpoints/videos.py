from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import uuid

from core.database import get_db
from models.video import VideoProject, PipelineStage, ComplianceReport, VideoAnalytics
from schemas.video import (
    VideoProjectCreate, VideoProjectUpdate, VideoProjectResponse,
    ComplianceReportResponse,
)

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
):
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(video, field, value)

    await db.flush()
    await db.refresh(video)
    return video


@router.patch("/{video_id}/stage", response_model=VideoProjectResponse)
async def advance_video_stage(
    video_id: uuid.UUID,
    stage_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")

    new_stage = stage_data.get("stage")
    if new_stage not in STAGE_ORDER:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {new_stage}")

    # Quality gate check before advancing to review
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
):
    result = await db.execute(
        select(ComplianceReport).where(ComplianceReport.video_project_id == video_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Compliance report not found. Run compliance check first.")
    return report


@router.post("/{video_id}/compliance/run", status_code=202)
async def run_compliance_check(
    video_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger Originality & Transformation Agent + Rights & Risk Agent."""
    result = await db.execute(select(VideoProject).where(VideoProject.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video project not found")

    # In production: background_tasks.add_task(run_compliance_agents, video_id)
    return {"message": "Compliance check queued", "video_id": str(video_id)}
