"""
Agent #13: Asset Retrieval — Layer 3 (AI Production Engine)

Retrieves B-roll footage, images, and music assets for each scene in the storyboard.
Uses free/licensed stock APIs (Pexels, Pixabay) and DALL-E for custom image generation.

Quality Gate: asset_coverage >= 80% (at least 80% of scenes have assets)
"""
import json
import time
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


ASSET_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a video asset coordinator. Given a storyboard scene, generate
optimal search queries to find matching B-roll footage and images.

For each scene generate:
1. A primary stock footage search query (3-5 keywords, specific)
2. A fallback image search query (3-5 keywords, simpler)
3. A DALL-E prompt for custom image generation (as last resort)
4. Music mood tags for this scene (2-3 tags from: upbeat, dramatic, calm, inspiring,
   suspenseful, playful, corporate, emotional)

RESPOND AS JSON:
{{
  "scenes": [
    {{
      "scene_id": "...",
      "footage_query": "...",
      "image_query": "...",
      "dalle_prompt": "...",
      "music_mood": ["upbeat", "inspiring"],
      "preferred_asset_type": "footage|image|animation"
    }}
  ]
}}"""),
    ("human", """Storyboard scenes:
{scenes}

Visual style: {visual_style}
Channel niche: {niche}
Language/culture: {language}"""),
])


class AssetRetrievalAgent(BaseAgent):
    agent_id = "asset_retrieval"
    layer = 3
    description = "Retrieves B-roll footage and images for each storyboard scene via Pexels/Pixabay/DALL-E"
    tools = ["Pexels API", "Pixabay API", "DALL-E 3", "ElevenLabs Music"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("plan_queries", self._plan_queries)
        workflow.add_node("fetch_assets", self._fetch_assets)
        workflow.add_node("quality_gate", self._quality_gate)

        workflow.add_edge(START, "plan_queries")
        workflow.add_edge("plan_queries", "fetch_assets")
        workflow.add_edge("fetch_assets", "quality_gate")
        workflow.add_edge("quality_gate", END)

        return workflow.compile(checkpointer=self._checkpointer)

    async def _plan_queries(self, state: AgentState) -> AgentState:
        """Generate search queries for each storyboard scene."""
        input_data = state["input_data"]
        scenes = input_data.get("scenes", [])

        if not scenes:
            state["output_data"]["queries"] = []
            state["errors"].append("No storyboard scenes provided")
            return state

        # MICRO tier — scene-to-query mapping is straightforward
        llm = self.get_routed_llm("extract_keywords")
        chain = ASSET_QUERY_PROMPT | llm

        response = await chain.ainvoke({
            "scenes": json.dumps(scenes[:20], ensure_ascii=False),  # max 20 scenes
            "visual_style": input_data.get("visual_style", "modern, clean, professional"),
            "niche": input_data.get("niche", ""),
            "language": input_data.get("language", "en"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            queries = json.loads(content.strip()).get("scenes", [])
        except (json.JSONDecodeError, IndexError):
            queries = []

        state["output_data"]["queries"] = queries
        return state

    async def _fetch_assets(self, state: AgentState) -> AgentState:
        """
        Attempt to fetch assets from Pexels API.
        Falls back to Pixabay, then generates DALL-E placeholder URLs.
        In production: integrate real Pexels/Pixabay/DALL-E SDK calls.
        """
        from core.config import settings

        queries = state["output_data"].get("queries", [])
        assets: List[Dict] = []

        for scene_query in queries:
            scene_id = scene_query.get("scene_id", f"scene_{len(assets)}")
            footage_query = scene_query.get("footage_query", "")

            # Attempt Pexels API
            asset = await self._fetch_from_pexels(footage_query, scene_id)

            if not asset:
                # Fallback: Pixabay
                asset = await self._fetch_from_pixabay(
                    scene_query.get("image_query", footage_query), scene_id
                )

            if not asset:
                # Last resort: DALL-E placeholder (in prod: call OpenAI Images API)
                asset = {
                    "scene_id": scene_id,
                    "type": "dalle_placeholder",
                    "url": None,
                    "dalle_prompt": scene_query.get("dalle_prompt", ""),
                    "status": "pending_generation",
                    "music_mood": scene_query.get("music_mood", ["calm"]),
                }

            assets.append(asset)

        state["output_data"]["assets"] = assets
        return state

    async def _fetch_from_pexels(self, query: str, scene_id: str) -> Dict:
        """Fetch stock footage from Pexels API."""
        from core.config import settings
        import httpx

        pexels_key = getattr(settings, "pexels_api_key", None)
        if not pexels_key or not query:
            return {}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.pexels.com/videos/search",
                    params={"query": query, "per_page": 3, "size": "medium"},
                    headers={"Authorization": pexels_key},
                )
                if response.status_code == 200:
                    data = response.json()
                    videos = data.get("videos", [])
                    if videos:
                        video = videos[0]
                        # Prefer HD file
                        files = sorted(
                            video.get("video_files", []),
                            key=lambda f: f.get("width", 0), reverse=True
                        )
                        url = files[0]["link"] if files else None
                        return {
                            "scene_id": scene_id,
                            "type": "footage",
                            "source": "pexels",
                            "url": url,
                            "pexels_id": video.get("id"),
                            "duration": video.get("duration"),
                            "status": "ready",
                        }
        except Exception:
            pass
        return {}

    async def _fetch_from_pixabay(self, query: str, scene_id: str) -> Dict:
        """Fetch stock image from Pixabay API."""
        from core.config import settings
        import httpx

        pixabay_key = getattr(settings, "pixabay_api_key", None)
        if not pixabay_key or not query:
            return {}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://pixabay.com/api/",
                    params={
                        "key": pixabay_key,
                        "q": query,
                        "image_type": "photo",
                        "per_page": 3,
                        "safesearch": "true",
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get("hits", [])
                    if hits:
                        img = hits[0]
                        return {
                            "scene_id": scene_id,
                            "type": "image",
                            "source": "pixabay",
                            "url": img.get("largeImageURL"),
                            "pixabay_id": img.get("id"),
                            "status": "ready",
                        }
        except Exception:
            pass
        return {}

    async def _quality_gate(self, state: AgentState) -> AgentState:
        assets = state["output_data"].get("assets", [])
        queries = state["output_data"].get("queries", [])

        total = len(queries)
        if total == 0:
            coverage = 0.0
        else:
            ready = sum(1 for a in assets if a.get("status") == "ready")
            coverage = ready / total * 100

        gate_passed = coverage >= 80.0

        state["output_data"]["summary"] = {
            "total_scenes": total,
            "assets_ready": sum(1 for a in assets if a.get("status") == "ready"),
            "assets_pending_dalle": sum(1 for a in assets if a.get("status") == "pending_generation"),
            "asset_coverage_pct": round(coverage, 1),
            "quality_gate_passed": gate_passed,
            "message": (
                f"Asset coverage {coverage:.0f}% — gate {'PASSED' if gate_passed else 'FAILED'} (threshold: 80%)"
            ),
        }
        state["quality_scores"]["asset_coverage"] = coverage
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


asset_retrieval_agent = AssetRetrievalAgent()
