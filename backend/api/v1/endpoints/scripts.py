from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from core.database import get_db
from models.video import Script
from schemas.video import ScriptGenerateRequest, ScriptResponse

router = APIRouter(prefix="/scripts", tags=["scripts"])


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.post("/generate", response_model=dict, status_code=202)
async def generate_script(
    request: ScriptGenerateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger Script Strategist + Hook Specialist + Retention Editor agents.
    Returns a run_id to poll for results.
    """
    run_id = str(uuid.uuid4())
    # In production: background_tasks.add_task(run_script_pipeline, request, run_id)
    return {
        "run_id": run_id,
        "status": "queued",
        "message": "Script generation pipeline queued: Script Strategist → Hook Specialist → Retention Editor",
        "estimated_duration_seconds": 250,
    }


@router.post("/{script_id}/optimize", response_model=dict, status_code=202)
async def optimize_script(
    script_id: uuid.UUID,
    optimize_data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Script).where(Script.id == script_id))
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    aspect = optimize_data.get("aspect", "retention")
    valid_aspects = ["hook", "retention", "naturalness", "originality", "cta"]
    if aspect not in valid_aspects:
        raise HTTPException(status_code=400, detail=f"Invalid aspect. Choose from: {valid_aspects}")

    run_id = str(uuid.uuid4())
    return {
        "run_id": run_id,
        "status": "queued",
        "aspect": aspect,
        "message": f"Script optimization ({aspect}) queued via Retention Editor Agent",
    }
