from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid
from datetime import datetime, timezone

from core.database import get_db
from core.auth import get_current_user, require_creator
from core.rate_limit import limiter
from models.user import User
from models.agent import AgentRun, AgentStatus
from schemas.agent import AgentInfo, AgentRunRequest, AgentRunResponse

router = APIRouter(prefix="/agents", tags=["agents"])

# Registry of all 23 agents
AGENT_REGISTRY = {
    # Layer 1 - Strategic
    "niche_hunter": {"name": "Niche Hunter", "layer": 1, "avg_duration": 45,
                     "tools": ["YouTube Data API", "Google Trends API", "vidIQ", "SimilarWeb"]},
    "opportunity_mapper": {"name": "Opportunity Mapper", "layer": 1, "avg_duration": 30,
                           "tools": ["Niche Hunter output", "keyword tools", "Google Trends"]},
    "competitive_deconstruction": {"name": "Competitive Deconstruction", "layer": 1, "avg_duration": 60,
                                   "tools": ["YouTube Analytics API", "competitor channel data"]},
    # Layer 2 - Content Design
    "channel_architect": {"name": "Channel Architect", "layer": 2, "avg_duration": 90,
                          "tools": ["Competitive Deconstruction output", "niche data", "brand templates"]},
    "script_strategist": {"name": "Script Strategist", "layer": 2, "avg_duration": 120,
                          "tools": ["Channel Architect output", "topic brief", "audience data"]},
    "voice_persona": {"name": "Voice Persona", "layer": 2, "avg_duration": 40,
                      "tools": ["Channel Architect output", "ElevenLabs voice library"]},
    # Layer 3 - Production
    "hook_specialist": {"name": "Hook Specialist", "layer": 3, "avg_duration": 50,
                        "tools": ["15 hook schemas", "top-performing hooks RAG", "A/B test history"]},
    "retention_editor": {"name": "Retention Editor", "layer": 3, "avg_duration": 80,
                         "tools": ["Script draft", "retention curve patterns"]},
    "thumbnail_psychology": {"name": "Thumbnail Psychology", "layer": 3, "avg_duration": 60,
                              "tools": ["7 thumbnail elements", "saliency heatmap", "competitor thumbnails"]},
    "title_architect": {"name": "Title Architect", "layer": 3, "avg_duration": 30,
                        "tools": ["Keyword data", "competitor titles", "CTR patterns"]},
    "storyboard": {"name": "Storyboard & Visual Beat", "layer": 3, "avg_duration": 100,
                   "tools": ["Script", "voice track timing", "visual style guide"]},
    "format_localizer": {"name": "Format Localizer", "layer": 3, "avg_duration": 70,
                         "tools": ["Finished video", "platform best practices"]},
    "asset_retrieval": {"name": "Asset Retrieval", "layer": 3, "avg_duration": 90,
                        "tools": ["Storyboard", "Pexels/Pixabay/Storyblocks APIs", "DALL-E"]},
    "video_assembly": {"name": "Video Assembly", "layer": 3, "avg_duration": 180,
                       "tools": ["Storyboard", "assets", "voice track", "FFmpeg pipeline"]},
    "audio_polish": {"name": "Audio Polish", "layer": 3, "avg_duration": 120,
                     "tools": ["Raw voice track", "background music", "SFX library"]},
    "caption": {"name": "Caption & Accessibility", "layer": 3, "avg_duration": 60,
                "tools": ["Video file", "Whisper/AssemblyAI transcription", "translation APIs"]},
    # Layer 4 - Growth
    "seo_intelligence": {"name": "SEO Intelligence", "layer": 4, "avg_duration": 45,
                         "tools": ["YouTube Search API", "keyword tools", "recommendation patterns"]},
    "experimentation": {"name": "Experimentation", "layer": 4, "avg_duration": 30,
                        "tools": ["YouTube Analytics API", "Test & Compare API"]},
    "watch_time_forensics": {"name": "Watch-Time Forensics", "layer": 4, "avg_duration": 60,
                             "tools": ["YouTube Analytics retention data", "video metadata"]},
    # Layer 5 - Compliance
    "channel_portfolio": {"name": "Channel Portfolio", "layer": 5, "avg_duration": 150,
                          "tools": ["All channel data", "market intelligence"]},
    "originality_transformation": {"name": "Originality & Transformation", "layer": 5, "avg_duration": 90,
                                   "tools": ["Embedding similarity (pgvector)", "cross-video analysis"]},
    "rights_risk": {"name": "Rights & Risk", "layer": 5, "avg_duration": 45,
                    "tools": ["Asset metadata", "music licensing databases", "Content ID patterns"]},
    "monetization_readiness": {"name": "Monetization Readiness", "layer": 5, "avg_duration": 30,
                               "tools": ["YouTube Analytics", "YPP thresholds", "ad policy checks"]},
}


@router.get("", response_model=List[AgentInfo])
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agents = []
    for agent_id, info in AGENT_REGISTRY.items():
        # Get stats from DB
        result = await db.execute(
            select(AgentRun).where(AgentRun.agent_id == agent_id)
        )
        runs = result.scalars().all()
        completed = [r for r in runs if r.status == AgentStatus.completed]
        success_rate = (len(completed) / len(runs) * 100) if runs else 0.0

        agents.append(AgentInfo(
            id=agent_id,
            name=info["name"],
            layer=info["layer"],
            description=f"Agent Layer {info['layer']}",
            status="idle",
            tasks_completed=len(completed),
            success_rate=round(success_rate, 1),
            avg_duration_seconds=info["avg_duration"],
            tools=info["tools"],
        ))
    return agents


@router.post("/{agent_id}/run", response_model=AgentRunResponse, status_code=202)
@limiter.limit("20/minute")
async def run_agent(
    request: Request,
    agent_id: str,
    run_request: AgentRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    run = AgentRun(
        agent_id=agent_id,
        video_project_id=run_request.video_project_id,
        channel_id=run_request.channel_id,
        status=AgentStatus.running,
        input_data=run_request.input_data,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)

    # Queue async execution
    if run_request.async_mode:
        background_tasks.add_task(
            _execute_agent_background,
            str(run.id),
            agent_id,
            run_request.input_data,
        )

    return run


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_run_status(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return run


@router.get("/{agent_id}/history", response_model=List[AgentRunResponse])
async def get_agent_history(
    agent_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def _execute_agent_background(run_id: str, agent_id: str, input_data: dict):
    """Dispatch to the correct Celery task for the given agent_id."""
    from tasks.agent_tasks import (
        run_niche_hunter, run_opportunity_mapper, run_competitive_deconstruction,
        run_channel_architect, run_script_strategist, run_voice_persona,
        run_hook_specialist, run_retention_editor,
        run_thumbnail_psychology, run_title_architect, run_storyboard,
        run_format_localizer, run_audio_polish, run_caption,
        run_asset_retrieval, run_video_assembly_agent,
        run_seo_intelligence, run_watch_time_forensics, run_experimentation,
        run_originality_check, run_rights_risk, run_monetization_readiness,
        run_channel_portfolio,
    )

    TASK_MAP = {
        "niche_hunter": run_niche_hunter,
        "opportunity_mapper": run_opportunity_mapper,
        "competitive_deconstruction": run_competitive_deconstruction,
        "channel_architect": run_channel_architect,
        "script_strategist": run_script_strategist,
        "voice_persona": run_voice_persona,
        "hook_specialist": run_hook_specialist,
        "retention_editor": run_retention_editor,
        "thumbnail_psychology": run_thumbnail_psychology,
        "title_architect": run_title_architect,
        "storyboard": run_storyboard,
        "format_localizer": run_format_localizer,
        "audio_polish": run_audio_polish,
        "caption": run_caption,
        "asset_retrieval": run_asset_retrieval,
        "video_assembly": run_video_assembly_agent,
        "seo_intelligence": run_seo_intelligence,
        "watch_time_forensics": run_watch_time_forensics,
        "experimentation": run_experimentation,
        "originality_transformation": run_originality_check,
        "rights_risk": run_rights_risk,
        "monetization_readiness": run_monetization_readiness,
        "channel_portfolio": run_channel_portfolio,
    }

    task = TASK_MAP.get(agent_id)
    if task:
        task.delay(run_id, input_data)
    else:
        import structlog
        structlog.get_logger(__name__).warning(
            "No Celery task for agent", agent_id=agent_id
        )
