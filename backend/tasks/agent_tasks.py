"""
Celery Tasks — Agent Execution
Każdy agent ma odpowiadający mu Celery task który:
1. Aktualizuje status run w DB
2. Wykonuje LangGraph graph
3. Zapisuje output i metryki
4. Wyzwala następny krok pipeline jeśli needed
"""
import asyncio
from datetime import datetime, timezone
from uuid import UUID

import structlog
from celery import shared_task

from core.celery_app import celery_app
from core.database import AsyncSessionLocal
from models.agent import AgentRun, AgentStatus
from sqlalchemy import select

logger = structlog.get_logger(__name__)


def run_async(coro):
    """Run async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _update_run_status(run_id: str, status: AgentStatus, output: dict = None, error: str = None):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AgentRun).where(AgentRun.id == UUID(run_id)))
        run = result.scalar_one_or_none()
        if run:
            run.status = status
            if output:
                run.output_data = output
            if error:
                run.error_message = error
            if status in (AgentStatus.completed, AgentStatus.error):
                run.completed_at = datetime.now(timezone.utc)
                if run.started_at:
                    run.duration_seconds = (run.completed_at - run.started_at).total_seconds()
            await db.commit()


# ============================================================
# Layer 1 — Market Intelligence
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_niche_hunter", max_retries=2)
def run_niche_hunter(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.strategic.niche_hunter import niche_hunter_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await niche_hunter_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)

    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_opportunity_mapper", max_retries=2)
def run_opportunity_mapper(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.strategic.opportunity_mapper import opportunity_mapper_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await opportunity_mapper_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)

    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_competitive_deconstruction", max_retries=2)
def run_competitive_deconstruction(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.strategic.competitive_deconstruction import competitive_deconstruction_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await competitive_deconstruction_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)

    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_channel_architect", max_retries=2)
def run_channel_architect(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.strategic.channel_architect import channel_architect_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await channel_architect_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)

    return run_async(_execute())


# ============================================================
# Layer 2 — Content Design
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_script_strategist", max_retries=2)
def run_script_strategist(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.content.script_strategist import script_strategist_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await script_strategist_agent.execute(input_data)

            # Auto-save script to DB
            if "script" in output and "error" not in output.get("script", {}):
                await _save_script_to_db(input_data.get("video_project_id"), output["script"])

            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)

    return run_async(_execute())


async def _save_script_to_db(video_project_id: str, script_data: dict):
    if not video_project_id:
        return
    from models.video import Script, VideoProject
    async with AsyncSessionLocal() as db:
        script = Script(
            video_project_id=UUID(video_project_id),
            title=script_data.get("title", ""),
            hook=script_data.get("sections", {}).get("hook", {}).get("text", ""),
            intro=script_data.get("sections", {}).get("intro", {}).get("text", ""),
            problem=script_data.get("sections", {}).get("problem", {}).get("text", ""),
            deepening=script_data.get("sections", {}).get("deepening", {}).get("text", ""),
            value=script_data.get("sections", {}).get("value", {}).get("text", ""),
            cta=script_data.get("sections", {}).get("cta", {}).get("text", ""),
            full_text=script_data.get("full_script", ""),
            word_count=script_data.get("word_count", 0),
            estimated_duration_seconds=int(script_data.get("estimated_duration_minutes", 12) * 60),
            hook_score=script_data.get("hook_score", 0),
            naturality_score=script_data.get("naturalness_score", 0),
            hook_variants=script_data.get("hook_variants", []),
        )
        db.add(script)

        # Update video project stage
        result = await db.execute(
            select(VideoProject).where(VideoProject.id == UUID(video_project_id))
        )
        video = result.scalar_one_or_none()
        if video:
            video.hook_score = script_data.get("hook_score")
            video.stage = "voice"  # advance to next stage
            video.assigned_agents = list(set((video.assigned_agents or []) + ["script_strategist"]))

        await db.commit()
        logger.info("Script saved to DB", video_project_id=video_project_id)


# ============================================================
# Layer 3 — Production
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_hook_specialist", max_retries=2)
def run_hook_specialist(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.content.hook_specialist import hook_specialist_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await hook_specialist_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_retention_editor", max_retries=2)
def run_retention_editor(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.content.retention_editor import retention_editor_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await retention_editor_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_thumbnail_psychology", max_retries=2)
def run_thumbnail_psychology(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.thumbnail_psychology import thumbnail_psychology_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await thumbnail_psychology_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_title_architect", max_retries=2)
def run_title_architect(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.title_architect import title_architect_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await title_architect_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_storyboard", max_retries=2)
def run_storyboard(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.storyboard_agent import storyboard_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await storyboard_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_format_localizer", max_retries=2)
def run_format_localizer(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.format_localizer import format_localizer_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await format_localizer_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_audio_polish", max_retries=2)
def run_audio_polish(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.audio_polish import audio_polish_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await audio_polish_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_caption", max_retries=2)
def run_caption(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.caption_agent import caption_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await caption_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


# ============================================================
# Layer 4 — Growth
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_seo_intelligence", max_retries=2)
def run_seo_intelligence(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.seo_intelligence import seo_intelligence_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await seo_intelligence_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_watch_time_forensics", max_retries=2)
def run_watch_time_forensics(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.growth.watch_time_forensics import watch_time_forensics_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await watch_time_forensics_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_experimentation", max_retries=2)
def run_experimentation(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.growth.experimentation_agent import experimentation_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await experimentation_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


# ============================================================
# Layer 5 — Compliance
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_originality_check", max_retries=2,
                 queue="high_priority")
def run_originality_check(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.compliance.originality_transformation import originality_transformation_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await originality_transformation_agent.execute(input_data)

            # Save compliance report
            if "final_report" in output:
                await _save_compliance_report(
                    input_data.get("video_project_id"),
                    output["final_report"]
                )

            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=15)

    return run_async(_execute())


async def _save_compliance_report(video_project_id: str, report_data: dict):
    if not video_project_id:
        return
    from models.video import ComplianceReport, RiskLevel
    async with AsyncSessionLocal() as db:
        # Upsert compliance report
        existing = await db.execute(
            select(ComplianceReport).where(
                ComplianceReport.video_project_id == UUID(video_project_id)
            )
        )
        report = existing.scalar_one_or_none()

        risk_map = {"green": RiskLevel.green, "yellow": RiskLevel.yellow, "red": RiskLevel.red}

        if not report:
            report = ComplianceReport(video_project_id=UUID(video_project_id))
            db.add(report)

        report.originality_score = report_data.get("originality_score", 0)
        report.similarity_to_other_videos = 1 - report_data.get("similarity_score", 1)
        report.template_overuse_risk = risk_map.get(
            report_data.get("template_overuse_risk", "green"), RiskLevel.green
        )
        report.ypp_safe = report_data.get("youtube_policy_compliance", True)
        report.issues = [
            {"severity": "yellow", "description": rf}
            for rf in report_data.get("risk_factors", [])
        ]
        report.recommendations = report_data.get("remediation", [])

        await db.commit()


@celery_app.task(bind=True, name="tasks.agent_tasks.run_rights_risk", max_retries=2,
                 queue="high_priority")
def run_rights_risk(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.compliance.rights_risk import rights_risk_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await rights_risk_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=15)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_monetization_readiness", max_retries=2)
def run_monetization_readiness(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.compliance.monetization_readiness import monetization_readiness_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await monetization_readiness_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


# ============================================================
# Full Pipeline Task — chains all agents
# ============================================================

@celery_app.task(name="tasks.agent_tasks.run_full_video_pipeline")
def run_full_video_pipeline(video_project_id: str, channel_id: str, input_data: dict):
    """
    Orchestrates the full production pipeline for one video.
    Chains: Script → Voice → Thumbnail → SEO → Compliance → Publish
    """
    from celery import chain
    import uuid

    run_ids = {agent: str(uuid.uuid4()) for agent in [
        "script_strategist", "hook_specialist", "retention_editor",
        "thumbnail_psychology", "title_architect", "seo_intelligence",
        "originality_check"
    ]}

    enriched_input = {**input_data, "video_project_id": video_project_id, "channel_id": channel_id}

    pipeline = chain(
        run_script_strategist.si(run_ids["script_strategist"], enriched_input),
        run_originality_check.si(run_ids["originality_check"], enriched_input),
    )
    pipeline.apply_async()

    return {"pipeline_started": True, "run_ids": run_ids}


# ============================================================
# Layer 2 — Content Design (additional)
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_voice_persona", max_retries=2)
def run_voice_persona(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.content.voice_persona import voice_persona_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await voice_persona_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


# ============================================================
# Layer 3 — Production (additional)
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_asset_retrieval", max_retries=2)
def run_asset_retrieval(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.asset_retrieval import asset_retrieval_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await asset_retrieval_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.agent_tasks.run_video_assembly_agent",
                 max_retries=1, queue="video_rendering", time_limit=1800)
def run_video_assembly_agent(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.production.video_assembly import video_assembly_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await video_assembly_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=60)
    return run_async(_execute())


# ============================================================
# Layer 5 — Compliance / Portfolio (additional)
# ============================================================

@celery_app.task(bind=True, name="tasks.agent_tasks.run_channel_portfolio", max_retries=2)
def run_channel_portfolio(self, run_id: str, input_data: dict):
    async def _execute():
        try:
            from agents.strategic.channel_portfolio import channel_portfolio_agent
            await _update_run_status(run_id, AgentStatus.running)
            output = await channel_portfolio_agent.execute(input_data)
            await _update_run_status(run_id, AgentStatus.completed, output)
            return output
        except Exception as exc:
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=30)
    return run_async(_execute())
