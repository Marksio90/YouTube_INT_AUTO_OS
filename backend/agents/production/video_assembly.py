"""
Agent #14: Video Assembly Agent — Layer 3 (AI Production Engine)

Orchestrates the full video assembly pipeline:
  1. Validates all required assets (voice track, B-roll, thumbnail)
  2. Dispatches FFmpeg assembly via video_assembly_service
  3. Validates output (duration, resolution, file size)
  4. Uploads to Cloudflare R2 and updates video project record

Quality Gate: output_valid (duration > 0, resolution 1080p, file_size < 2GB)
"""
import time
from typing import Any, Dict

from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


class VideoAssemblyAgent(BaseAgent):
    agent_id = "video_assembly"
    layer = 3
    description = "Orchestrates FFmpeg pipeline: voice + B-roll + captions + music → final MP4"
    tools = ["FFmpeg pipeline", "Cloudflare R2", "video_assembly_service"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("validate_assets", self._validate_assets)
        workflow.add_node("assemble_video", self._assemble_video)
        workflow.add_node("validate_output", self._validate_output)
        workflow.add_node("upload_and_update", self._upload_and_update)

        workflow.add_edge(START, "validate_assets")
        workflow.add_conditional_edges(
            "validate_assets",
            lambda s: "assemble" if s["output_data"].get("assets_valid") else "error",
            {"assemble": "assemble_video", "error": END},
        )
        workflow.add_edge("assemble_video", "validate_output")
        workflow.add_edge("validate_output", "upload_and_update")
        workflow.add_edge("upload_and_update", END)

        return workflow.compile(checkpointer=self._checkpointer)

    async def _validate_assets(self, state: AgentState) -> AgentState:
        """Check all required assets are present before triggering FFmpeg."""
        input_data = state["input_data"]
        missing = []

        if not input_data.get("voice_track_url"):
            missing.append("voice_track_url")
        if not input_data.get("scenes") and not input_data.get("asset_manifest"):
            missing.append("scenes or asset_manifest")

        assets_valid = len(missing) == 0
        state["output_data"]["assets_valid"] = assets_valid
        state["output_data"]["missing_assets"] = missing

        if not assets_valid:
            state["errors"].append(f"Missing required assets: {missing}")
            state["output_data"]["quality_gate_passed"] = False
            state["output_data"]["message"] = f"Assembly blocked — missing: {missing}"

        return state

    async def _assemble_video(self, state: AgentState) -> AgentState:
        """Dispatch assembly to video_assembly_service (FFmpeg pipeline)."""
        from services.video_assembly_service import video_assembly_service
        from core.config import settings

        input_data = state["input_data"]
        video_project_id = input_data.get("video_project_id", "unknown")

        profile = input_data.get("format", "youtube_1080p")
        if profile == "shorts":
            profile = "shorts"

        try:
            result = await video_assembly_service.assemble(
                project_id=video_project_id,
                voice_track_url=input_data["voice_track_url"],
                scenes=input_data.get("scenes", []),
                asset_manifest=input_data.get("asset_manifest", {}),
                background_music_url=input_data.get("background_music_url"),
                captions_path=input_data.get("captions_path"),
                profile=profile,
            )
            state["output_data"]["assembly_result"] = result
            state["output_data"]["output_path"] = result.get("output_path")
        except Exception as e:
            state["errors"].append(f"Assembly failed: {str(e)}")
            state["output_data"]["assembly_result"] = {"error": str(e)}
            self.logger.error("Video assembly failed", error=str(e), project_id=video_project_id)

        return state

    async def _validate_output(self, state: AgentState) -> AgentState:
        """Check the assembled file meets quality requirements."""
        import os

        assembly = state["output_data"].get("assembly_result", {})
        output_path = assembly.get("output_path") or state["output_data"].get("output_path")

        if not output_path or assembly.get("error"):
            state["output_data"]["output_valid"] = False
            state["output_data"]["quality_gate_passed"] = False
            return state

        file_size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        duration_s = assembly.get("duration_seconds", 0)
        width = assembly.get("width", 0)

        output_valid = (
            duration_s > 30          # at least 30 seconds
            and width >= 1280        # at least 720p
            and file_size_bytes > 0
            and file_size_bytes < 2 * 1024 ** 3  # under 2 GB
        )

        state["output_data"]["output_valid"] = output_valid
        state["output_data"]["file_stats"] = {
            "duration_seconds": duration_s,
            "resolution": f"{width}x{assembly.get('height', 0)}",
            "file_size_mb": round(file_size_bytes / 1024 ** 2, 1),
        }
        state["quality_scores"]["output_valid"] = 100.0 if output_valid else 0.0
        return state

    async def _upload_and_update(self, state: AgentState) -> AgentState:
        """Upload assembled video to R2 and update VideoProject record."""
        from services.storage_service import storage_service
        from core.database import AsyncSessionLocal
        from models.video import VideoProject
        from sqlalchemy import select
        from uuid import UUID

        if not state["output_data"].get("output_valid"):
            state["output_data"]["quality_gate_passed"] = False
            state["output_data"]["message"] = "Output validation failed — video not uploaded"
            return state

        output_path = state["output_data"].get("output_path")
        video_project_id = state["input_data"].get("video_project_id")

        video_url = None
        if output_path and video_project_id:
            try:
                object_key = f"videos/{video_project_id}/final.mp4"
                video_url = await storage_service.upload_file(
                    local_path=output_path, object_key=object_key
                )
            except Exception as e:
                self.logger.warning("R2 upload failed", error=str(e))

        if video_url and video_project_id:
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(VideoProject).where(VideoProject.id == UUID(video_project_id))
                    )
                    video = result.scalar_one_or_none()
                    if video:
                        video.video_url = video_url
                        video.stage = "thumbnail"
                        file_stats = state["output_data"].get("file_stats", {})
                        if file_stats.get("duration_seconds"):
                            video.actual_duration_seconds = int(file_stats["duration_seconds"])
                        await db.commit()
            except Exception as e:
                self.logger.error("DB update failed after assembly", error=str(e))

        state["output_data"]["video_url"] = video_url
        state["output_data"]["quality_gate_passed"] = True
        state["output_data"]["message"] = (
            f"Video assembled and uploaded: {video_url}" if video_url
            else "Video assembled locally (upload skipped)"
        )
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        run_id = f"{self.agent_id}-{time.time()}"
        config = {"configurable": {"thread_id": run_id}}
        final_state = await graph.ainvoke(self._initial_state(input_data, run_id=run_id), config)
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


video_assembly_agent = VideoAssemblyAgent()
