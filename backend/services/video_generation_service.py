"""
AI Video Generation Service — Kling AI + Runway Gen-4
Generuje krótkie klipy wideo z tekstu lub obrazu, używane jako B-roll.

Providers:
  - Kling AI (kling-v2-master): $0.029/s, max 10s, text→video lub image→video
  - Runway Gen-4 Turbo: $0.05/s, max 10s, text→video lub image→video

Fallback chain:
  1. Kling AI (tańszy, szybszy)
  2. Runway Gen-4 (fallback gdy Kling niedostępny)
  3. Pexels/stock (gdy oboje niedostępni)

Integracja z asset_service: metoda generate_video_ai() automatycznie
wybiera provider i zwraca tę samą strukturę co search_pexels_video().
"""
import asyncio
import time
import hashlib
import jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Literal
import httpx
import structlog

from core.config import settings
from core.langfuse import create_trace

logger = structlog.get_logger(__name__)

KLING_API_BASE = "https://api.klingai.com"
RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"

VideoProvider = Literal["kling", "runway", "none"]


class VideoGenerationService:
    def __init__(self):
        self.kling_api_key = settings.kling_api_key
        self.runway_api_key = settings.runway_api_key

    @property
    def kling_available(self) -> bool:
        return bool(self.kling_api_key)

    @property
    def runway_available(self) -> bool:
        return bool(self.runway_api_key)

    @property
    def any_available(self) -> bool:
        return self.kling_available or self.runway_available

    def preferred_provider(self) -> VideoProvider:
        if self.kling_available:
            return "kling"
        if self.runway_available:
            return "runway"
        return "none"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_video(
        self,
        prompt: str,
        scene_index: int,
        duration_seconds: int = 5,
        image_url: Optional[str] = None,
        provider: Optional[VideoProvider] = None,
    ) -> Dict:
        """
        Generate a short AI video clip for a storyboard scene.
        Returns same structure as asset_service stock video results.

        Args:
            prompt: Scene description
            scene_index: Storyboard scene number
            duration_seconds: Desired clip length (5 or 10 seconds)
            image_url: Optional reference image for image→video mode
            provider: Force specific provider, or None for auto-select
        """
        chosen = provider or self.preferred_provider()

        trace = create_trace(
            name=f"ai_video_generation_{chosen}",
            input_data={"prompt": prompt, "duration": duration_seconds, "scene_index": scene_index},
            tags=["video_generation", chosen],
        )

        try:
            if chosen == "kling" and self.kling_available:
                result = await self._generate_kling(prompt, scene_index, duration_seconds, image_url)
            elif chosen == "runway" and self.runway_available:
                result = await self._generate_runway(prompt, scene_index, duration_seconds, image_url)
            else:
                logger.warning("No AI video provider configured", scene_index=scene_index)
                return {"scene_index": scene_index, "type": "none", "url": None}

            if trace and result.get("url"):
                trace.update(
                    output={"url": result["url"], "provider": chosen},
                    metadata={"cost_usd": result.get("cost", 0)},
                )
            return result

        except Exception as e:
            logger.error("AI video generation failed", provider=chosen, scene_index=scene_index, error=str(e))
            if trace:
                trace.update(output={"error": str(e)})

            # Auto-fallback: try Runway if Kling failed
            if chosen == "kling" and self.runway_available:
                logger.info("Falling back to Runway after Kling failure", scene_index=scene_index)
                try:
                    return await self._generate_runway(prompt, scene_index, duration_seconds, image_url)
                except Exception as e2:
                    logger.error("Runway fallback also failed", error=str(e2))

            return {"scene_index": scene_index, "type": "none", "url": None}

    # ------------------------------------------------------------------
    # Kling AI
    # ------------------------------------------------------------------

    def _kling_jwt_token(self) -> str:
        """Generate Kling API JWT token from API key (format: access_key:secret_key)."""
        if ":" not in self.kling_api_key:
            # Already a bare token
            return self.kling_api_key

        access_key, secret_key = self.kling_api_key.split(":", 1)
        now = int(time.time())
        payload = {
            "iss": access_key,
            "exp": now + 1800,  # 30 minutes
            "nbf": now - 5,
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    async def _generate_kling(
        self,
        prompt: str,
        scene_index: int,
        duration_seconds: int,
        image_url: Optional[str],
    ) -> Dict:
        """Generate video with Kling AI API."""
        token = self._kling_jwt_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Choose endpoint: text→video or image→video
        if image_url:
            endpoint = f"{KLING_API_BASE}/v1/videos/image2video"
            body = {
                "model_name": "kling-v2-master",
                "image_url": image_url,
                "prompt": prompt,
                "duration": str(min(duration_seconds, 10)),
                "cfg_scale": 0.5,
            }
        else:
            endpoint = f"{KLING_API_BASE}/v1/videos/text2video"
            body = {
                "model_name": "kling-v2-master",
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, watermark, text overlay",
                "duration": str(min(duration_seconds, 10)),
                "aspect_ratio": "16:9",
                "cfg_scale": 0.5,
            }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        task_id = data.get("data", {}).get("task_id")
        if not task_id:
            raise Exception(f"Kling: no task_id in response: {data}")

        logger.info("Kling video task created", task_id=task_id, scene_index=scene_index)

        # Poll for completion
        video_url = await self._poll_kling_task(task_id, headers)
        cost = duration_seconds * 0.029  # $0.029/s

        return {
            "scene_index": scene_index,
            "type": "video",
            "source": "kling_ai",
            "url": video_url,
            "duration": duration_seconds,
            "query": prompt,
            "cost": round(cost, 4),
        }

    async def _poll_kling_task(self, task_id: str, headers: dict, max_wait: int = 300) -> str:
        """Poll Kling task until video is ready. Returns video URL."""
        poll_url = f"{KLING_API_BASE}/v1/videos/text2video/{task_id}"
        start = time.time()

        while time.time() - start < max_wait:
            await asyncio.sleep(5)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(poll_url, headers=headers)
                response.raise_for_status()
                data = response.json()

            task_data = data.get("data", {})
            status = task_data.get("task_status", "")

            if status == "succeed":
                works = task_data.get("task_result", {}).get("videos", [])
                if works:
                    return works[0].get("url", "")
                raise Exception("Kling: task succeeded but no video URL")

            if status in ("failed", "cancelled"):
                msg = task_data.get("task_status_msg", "unknown error")
                raise Exception(f"Kling task {status}: {msg}")

            logger.debug("Kling task pending", task_id=task_id, status=status)

        raise Exception(f"Kling task timed out after {max_wait}s")

    # ------------------------------------------------------------------
    # Runway Gen-4
    # ------------------------------------------------------------------

    async def _generate_runway(
        self,
        prompt: str,
        scene_index: int,
        duration_seconds: int,
        image_url: Optional[str],
    ) -> Dict:
        """Generate video with Runway Gen-4 Turbo API."""
        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

        # Runway supports 5s or 10s durations
        duration = 10 if duration_seconds >= 8 else 5

        body = {
            "model": "gen4_turbo",
            "promptText": prompt,
            "ratio": "1280:720",
            "duration": duration,
        }
        if image_url:
            body["promptImage"] = image_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{RUNWAY_API_BASE}/image_to_video",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        task_id = data.get("id")
        if not task_id:
            raise Exception(f"Runway: no task id in response: {data}")

        logger.info("Runway task created", task_id=task_id, scene_index=scene_index)

        # Poll for completion
        video_url = await self._poll_runway_task(task_id, headers)
        cost = duration * 0.05  # $0.05/s

        return {
            "scene_index": scene_index,
            "type": "video",
            "source": "runway_gen4",
            "url": video_url,
            "duration": duration,
            "query": prompt,
            "cost": round(cost, 4),
        }

    async def _poll_runway_task(self, task_id: str, headers: dict, max_wait: int = 300) -> str:
        """Poll Runway task until video is ready. Returns video URL."""
        poll_url = f"{RUNWAY_API_BASE}/tasks/{task_id}"
        start = time.time()

        while time.time() - start < max_wait:
            await asyncio.sleep(5)

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(poll_url, headers=headers)
                response.raise_for_status()
                data = response.json()

            status = data.get("status", "")

            if status == "SUCCEEDED":
                outputs = data.get("output", [])
                if outputs:
                    return outputs[0]
                raise Exception("Runway: task SUCCEEDED but no output URL")

            if status == "FAILED":
                error = data.get("failure", "unknown error")
                raise Exception(f"Runway task failed: {error}")

            logger.debug("Runway task pending", task_id=task_id, status=status)

        raise Exception(f"Runway task timed out after {max_wait}s")

    # ------------------------------------------------------------------
    # Batch generation for storyboard
    # ------------------------------------------------------------------

    async def generate_videos_for_storyboard(
        self,
        storyboard: list,
        niche: str = "",
        max_concurrent: int = 3,
    ) -> list:
        """
        Generate AI video clips for all stock_video scenes in a storyboard.
        Respects max_concurrent to avoid API rate limits.
        """
        if not self.any_available:
            logger.warning("No AI video provider configured — skipping AI video generation")
            return [{"scene_index": i, "type": "none", "url": None} for i in range(len(storyboard))]

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _generate_with_limit(i: int, scene: dict) -> Dict:
            async with semaphore:
                prompt = scene.get("asset_query") or scene.get("description", f"{niche} scene")
                duration = min(int(scene.get("duration_seconds", 5)), 10)
                return await self.generate_video(
                    prompt=prompt,
                    scene_index=i,
                    duration_seconds=duration,
                )

        tasks = [
            _generate_with_limit(i, scene)
            for i, scene in enumerate(storyboard)
            if scene.get("asset_type") == "stock_video"
        ]

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            r if not isinstance(r, Exception) else {"scene_index": -1, "type": "none", "url": None}
            for r in results
        ]


video_generation_service = VideoGenerationService()
