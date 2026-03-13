from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_db
from core.auth import get_current_user, require_creator
from models.user import User
from models.agent import NicheAnalysis, AgentRun, AgentStatus
from schemas.agent import NicheAnalysisResponse

router = APIRouter(prefix="/niches", tags=["niches"])


@router.get("", response_model=List[NicheAnalysisResponse])
async def list_niches(
    channel_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all niche analyses, optionally filtered by channel."""
    query = select(NicheAnalysis)
    if channel_id:
        query = query.where(NicheAnalysis.channel_id == channel_id)
    query = query.order_by(NicheAnalysis.overall_score.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/analyze", status_code=202)
async def trigger_niche_analysis(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """
    Trigger niche analysis pipeline: Niche Hunter → Opportunity Mapper → Competitive Deconstruction.
    Returns a run_id for SSE polling.
    """
    niche_name = data.get("niche_name")
    if not niche_name:
        raise HTTPException(status_code=422, detail="niche_name is required")

    run = AgentRun(
        agent_id="niche_hunter",
        status=AgentStatus.running,
        input_data={
            "niche_name": niche_name,
            "category": data.get("category", ""),
            "channel_id": str(data["channel_id"]) if data.get("channel_id") else None,
        },
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    from api.v1.endpoints.agents import _execute_agent_background
    background_tasks.add_task(
        _execute_agent_background,
        str(run.id),
        "niche_hunter",
        run.input_data,
    )

    return {
        "run_id": str(run.id),
        "status": "queued",
        "message": "Niche analysis queued: Niche Hunter → Opportunity Mapper → Competitive Deconstruction",
        "stream_url": f"/api/v1/agents/runs/{run.id}/stream",
    }
