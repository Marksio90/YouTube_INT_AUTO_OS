"""
Celery Tasks — Video Production (FFmpeg heavy tasks)
Queue: video_rendering (dedicated workers)
"""
import asyncio
import structlog
from pathlib import Path

from core.celery_app import celery_app
from tasks.agent_tasks import run_async

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="tasks.video_tasks.generate_voice_over",
                 queue="default", max_retries=3)
def generate_voice_over(self, run_id: str, input_data: dict):
    """Generate ElevenLabs voice-over for script."""
    async def _execute():
        try:
            from services.tts_service import tts_service
            from tasks.agent_tasks import _update_run_status
            from models.agent import AgentStatus

            await _update_run_status(run_id, AgentStatus.running)

            audio_url = await tts_service.generate(
                text=input_data["script_text"],
                voice_id=input_data.get("voice_id"),
                video_project_id=input_data.get("video_project_id"),
            )

            output = {"audio_url": audio_url, "status": "completed"}
            await _update_run_status(run_id, AgentStatus.completed, output)

            # Update video project with audio URL
            if input_data.get("video_project_id"):
                from core.database import AsyncSessionLocal
                from models.video import VideoProject
                from sqlalchemy import select
                from uuid import UUID
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(VideoProject).where(
                            VideoProject.id == UUID(input_data["video_project_id"])
                        )
                    )
                    video = result.scalar_one_or_none()
                    if video:
                        video.voice_track_url = audio_url
                        video.stage = "video"
                        await db.commit()

            return output
        except Exception as exc:
            from tasks.agent_tasks import _update_run_status
            from models.agent import AgentStatus
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=60)

    return run_async(_execute())


@celery_app.task(bind=True, name="tasks.video_tasks.assemble_video",
                 queue="video_rendering", max_retries=2, time_limit=3600)
def assemble_video(self, run_id: str, input_data: dict):
    """
    FFmpeg video assembly task.
    Combines: voice track + B-roll assets + captions + music.
    """
    async def _execute():
        try:
            from services.video_assembly_service import video_assembly_service
            from tasks.agent_tasks import _update_run_status
            from models.agent import AgentStatus

            await _update_run_status(run_id, AgentStatus.running)

            result = await video_assembly_service.assemble(
                voice_track_url=input_data["voice_track_url"],
                storyboard=input_data["storyboard"],
                assets=input_data.get("assets", []),
                music_url=input_data.get("music_url"),
                captions_srt=input_data.get("captions_srt"),
                video_project_id=input_data.get("video_project_id"),
            )

            await _update_run_status(run_id, AgentStatus.completed, result)
            return result
        except Exception as exc:
            from tasks.agent_tasks import _update_run_status
            from models.agent import AgentStatus
            await _update_run_status(run_id, AgentStatus.error, error=str(exc))
            raise self.retry(exc=exc, countdown=120)

    return run_async(_execute())
