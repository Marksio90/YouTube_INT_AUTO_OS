"""
Asset Retrieval Service — Pexels + Pixabay + DALL-E
Pobiera lub generuje B-roll assets dla każdej sceny storyboardu.

Integracja:
- Pexels API (free, no attribution required for video)
- Pixabay API (free, commercial use OK)
- DALL-E 3 (generowane obrazy dla abstract/branded content)
- Storyblocks (paid subscription, premium footage)
"""
import asyncio
import hashlib
from typing import List, Dict, Optional, Literal
import httpx
from openai import AsyncOpenAI
import structlog

from core.config import settings
from core.langfuse import create_trace

logger = structlog.get_logger(__name__)

PEXELS_API_KEY = settings.pexels_api_key
PIXABAY_API_KEY = settings.pixabay_api_key


class AssetService:
    def __init__(self):
        self.openai = AsyncOpenAI(
            api_key=settings.openai_api_key,
            organization=settings.openai_org_id or None,
        )
        # Limit concurrent external API calls to avoid rate limits
        self._semaphore = asyncio.Semaphore(5)

    async def _find_asset_for_scene_limited(self, i: int, scene: Dict, niche: str, style: str) -> Dict:
        """Wrapper that enforces the concurrency semaphore."""
        async with self._semaphore:
            return await self._find_asset_for_scene(i, scene, niche, style)

    async def find_assets_for_storyboard(
        self, storyboard: List[Dict], niche: str = "", style: str = "professional"
    ) -> List[Dict]:
        """
        For each scene in storyboard, find/generate the best asset.
        Returns list of {scene_index, url, type, source, query, cost}.
        Max 5 concurrent external API calls to avoid rate limits.
        """
        assets = []
        tasks = [
            self._find_asset_for_scene_limited(i, scene, niche, style)
            for i, scene in enumerate(storyboard)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Asset retrieval failed", scene=i, error=str(result))
                assets.append({"scene_index": i, "type": "black", "url": None})
            else:
                assets.append(result)

        return assets

    async def _find_asset_for_scene(
        self, scene_index: int, scene: Dict, niche: str, style: str
    ) -> Dict:
        """Find best asset for a single scene."""
        scene_type = scene.get("asset_type", "stock_photo")  # stock_photo, stock_video, generated
        query = scene.get("asset_query") or scene.get("description", f"{niche} video")

        if scene_type == "generated":
            return await self.generate_image_dalle(query, scene_index)
        elif scene_type == "stock_video":
            # Prefer AI-generated video (Kling/Runway) over stock footage
            # Late import to avoid circular dependency at module load time
            try:
                from services.video_generation_service import video_generation_service
                if video_generation_service.any_available:
                    duration = min(int(scene.get("duration_seconds", 5)), 10)
                    result = await video_generation_service.generate_video(
                        prompt=query,
                        scene_index=scene_index,
                        duration_seconds=duration,
                    )
                    if result.get("url"):
                        return result
            except ImportError:
                pass
            # Fallback to Pexels stock video
            return await self.search_pexels_video(query, scene_index)
        else:
            # Try Pexels first, fallback to Pixabay, fallback to DALL-E
            result = await self.search_pexels_photo(query, scene_index)
            if not result.get("url"):
                result = await self.search_pixabay_photo(query, scene_index)
            if not result.get("url"):
                result = await self.generate_image_dalle(query, scene_index)
            return result

    async def search_pexels_photo(self, query: str, scene_index: int) -> Dict:
        """Search Pexels for stock photos."""
        if not PEXELS_API_KEY:
            return {"scene_index": scene_index, "type": "none", "url": None}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5, "orientation": "landscape"},
                timeout=10.0,
            )

        if response.status_code == 200:
            photos = response.json().get("photos", [])
            if photos:
                photo = photos[0]
                return {
                    "scene_index": scene_index,
                    "type": "image",
                    "source": "pexels",
                    "url": photo["src"]["large2x"],
                    "query": query,
                    "cost": 0.0,
                    "attribution": f"Photo by {photo['photographer']} from Pexels",
                }
        return {"scene_index": scene_index, "type": "none", "url": None}

    async def search_pexels_video(self, query: str, scene_index: int) -> Dict:
        """Search Pexels for short stock video clips."""
        if not PEXELS_API_KEY:
            return {"scene_index": scene_index, "type": "none", "url": None}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5, "min_duration": 3, "max_duration": 15},
                timeout=10.0,
            )

        if response.status_code == 200:
            videos = response.json().get("videos", [])
            if videos:
                video = videos[0]
                # Get HD file
                hd_file = next(
                    (f for f in video.get("video_files", []) if f.get("quality") == "hd"),
                    video.get("video_files", [{}])[0],
                )
                return {
                    "scene_index": scene_index,
                    "type": "video",
                    "source": "pexels",
                    "url": hd_file.get("link", ""),
                    "duration": video.get("duration", 10),
                    "query": query,
                    "cost": 0.0,
                }
        return {"scene_index": scene_index, "type": "none", "url": None}

    async def search_pixabay_photo(self, query: str, scene_index: int) -> Dict:
        """Search Pixabay for stock photos."""
        if not PIXABAY_API_KEY:
            return {"scene_index": scene_index, "type": "none", "url": None}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://pixabay.com/api/",
                params={
                    "key": PIXABAY_API_KEY,
                    "q": query,
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "safesearch": "true",
                    "per_page": 5,
                },
                timeout=10.0,
            )

        if response.status_code == 200:
            hits = response.json().get("hits", [])
            if hits:
                photo = hits[0]
                return {
                    "scene_index": scene_index,
                    "type": "image",
                    "source": "pixabay",
                    "url": photo["largeImageURL"],
                    "query": query,
                    "cost": 0.0,
                }
        return {"scene_index": scene_index, "type": "none", "url": None}

    async def generate_image_dalle(self, prompt: str, scene_index: int) -> Dict:
        """Generate image with DALL-E 3 (~$0.04/image at 1024x1024)."""
        trace = create_trace(
            name="dalle3_image_generation",
            input_data={"prompt": prompt, "scene_index": scene_index},
            tags=["dalle3", "image_generation"],
        )
        try:
            response = await self.openai.images.generate(
                model="dall-e-3",
                prompt=f"Professional YouTube video thumbnail or B-roll: {prompt}. Photorealistic, high quality, 16:9 aspect ratio.",
                size="1792x1024",
                quality="standard",
                n=1,
            )

            result = {
                "scene_index": scene_index,
                "type": "image",
                "source": "dalle3",
                "url": response.data[0].url,
                "revised_prompt": response.data[0].revised_prompt,
                "query": prompt,
                "cost": 0.04,  # $0.04 per image
            }
            if trace:
                trace.update(output={"url": result["url"]}, metadata={"cost_usd": 0.04})
            return result
        except Exception as e:
            logger.error("DALL-E generation failed", error=str(e))
            if trace:
                trace.update(output={"error": str(e)})
            return {"scene_index": scene_index, "type": "none", "url": None}

    async def generate_thumbnail_concepts(
        self, title: str, niche: str, style: str = "high_ctr", n: int = 3
    ) -> List[Dict]:
        """
        Generate N thumbnail concept images for A/B testing.
        Returns list of {url, concept, ctr_hypothesis}.
        """
        concepts = [
            f"Bold eye-catching YouTube thumbnail for '{title}'. Bright colors, clear text space, emotional face or dramatic graphic. {niche} content.",
            f"Minimalist high-contrast YouTube thumbnail for '{title}'. Clean design, one dominant element, strong typography space. {niche}.",
            f"Curiosity-gap YouTube thumbnail for '{title}'. Intriguing visual that makes viewer want to click. Before/after or question mark style. {niche}.",
        ][:n]

        tasks = [self.generate_image_dalle(concept, i) for i, concept in enumerate(concepts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        thumbnails = []
        for i, result in enumerate(results):
            if not isinstance(result, Exception) and result.get("url"):
                thumbnails.append({
                    "index": i,
                    "url": result["url"],
                    "concept": concepts[i][:100],
                    "ctr_hypothesis": 7.5 - i * 0.5,  # Placeholder — real scoring via CV service
                    "cost": result.get("cost", 0.04),
                })

        return thumbnails


asset_service = AssetService()
