from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from core.database import get_db
from core.auth import get_current_user, require_creator
from core.rate_limit import limiter
from models.user import User
from models.video import Script
from models.agent import AgentRun, AgentStatus
from schemas.video import ScriptGenerateRequest, ScriptResponse

router = APIRouter(prefix="/scripts", tags=["scripts"])


def _dispatch_script_pipeline(run_id: str, input_data: dict):
    """Dispatch script generation pipeline to Celery."""
    from tasks.agent_tasks import run_script_strategist
    run_script_strategist.delay(run_id, input_data)


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.post("/generate", response_model=dict, status_code=202)
@limiter.limit("10/minute")
async def generate_script(
    request_obj: Request,
    request: ScriptGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    """
    Trigger Script Strategist + Hook Specialist + Retention Editor agents.
    Returns a run_id to poll for results via SSE or GET /agents/runs/{run_id}.
    """
    run = AgentRun(
        agent_id="script_strategist",
        video_project_id=request.video_project_id,
        status=AgentStatus.running,
        input_data=request.model_dump(mode="json"),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    background_tasks.add_task(
        _dispatch_script_pipeline,
        str(run.id),
        request.model_dump(mode="json"),
    )

    return {
        "run_id": str(run.id),
        "status": "queued",
        "message": "Script generation pipeline queued: Script Strategist → Hook Specialist → Retention Editor",
        "estimated_duration_seconds": 250,
        "stream_url": f"/api/v1/agents/runs/{run.id}/stream",
    }


@router.post("/{script_id}/optimize", response_model=dict, status_code=202)
@limiter.limit("10/minute")
async def optimize_script(
    request_obj: Request,
    script_id: uuid.UUID,
    optimize_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    aspect = optimize_data.get("aspect", "retention")
    valid_aspects = ["hook", "retention", "naturalness", "originality", "cta"]
    if aspect not in valid_aspects:
        raise HTTPException(status_code=400, detail=f"Invalid aspect. Choose from: {valid_aspects}")

    agent_map = {
        "hook": "hook_specialist",
        "retention": "retention_editor",
        "naturalness": "script_strategist",
        "originality": "originality_transformation",
        "cta": "retention_editor",
    }
    agent_id = agent_map[aspect]

    run = AgentRun(
        agent_id=agent_id,
        video_project_id=script.video_project_id,
        status=AgentStatus.running,
        input_data={"script_id": str(script_id), "aspect": aspect, **optimize_data},
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    from api.v1.endpoints.agents import _execute_agent_background
    background_tasks.add_task(
        _execute_agent_background,
        str(run.id),
        agent_id,
        run.input_data,
    )

    return {
        "run_id": str(run.id),
        "status": "queued",
        "aspect": aspect,
        "message": f"Script optimization ({aspect}) queued via {agent_id} agent",
        "stream_url": f"/api/v1/agents/runs/{run.id}/stream",
    }
