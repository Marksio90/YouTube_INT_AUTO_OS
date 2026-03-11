"""
Agent #8: Thumbnail Psychology Agent — Layer 3 (Production)

Designs thumbnails using psychological principles and generates
DALL-E concept images for A/B testing.

Quality Gate: CTR potential >= 7%, brand consistency check.
Psychological frameworks: Cialdini, visual salience, F-pattern eye tracking.
"""
import json
import time
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


THUMBNAIL_DESIGN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube thumbnail psychology expert. You design thumbnails that maximize CTR using cognitive science.

THUMBNAIL PSYCHOLOGY PRINCIPLES:
1. F-PATTERN: Most important element top-left, second top-right
2. FACE EFFECT: Human faces with extreme emotions (surprise, shock, joy) boost CTR 35%
3. CONTRAST: Subject must be visible at 120x68px (mobile thumbnail size)
4. COLOR PSYCHOLOGY:
   - Red/Orange: Urgency, energy, excitement
   - Yellow: Optimism, curiosity, attention
   - Blue: Trust, authority, calm
   - Green: Growth, health, money
5. TEXT OVERLAY: 3-5 words max, largest 30% of thumbnail height
6. CURIOSITY GAP: Show result without full context
7. BEFORE/AFTER SPLIT: High engagement for transformation content
8. NEGATIVE SPACE: Don't fill every pixel — guide the eye

CTR BENCHMARK BY NICHE:
- Finance: 4-6% avg, 8%+ top performers
- Tech/Software: 3-5% avg, 7%+ top
- Health/Fitness: 5-7% avg, 10%+ top
- Education: 3-4% avg, 6%+ top
- Entertainment: 6-9% avg, 12%+ top

RESPOND AS JSON:
{{
  "thumbnail_concepts": [
    {{
      "concept_id": 1,
      "layout": "face_dominant|text_dominant|split_screen|before_after|minimal",
      "primary_element": "description of main visual",
      "text_overlay": "TEXT ON THUMBNAIL",
      "color_palette": ["#hex1", "#hex2", "#hex3"],
      "psychological_trigger": "curiosity|fear|desire|social_proof|authority",
      "face_emotion": "shock|excitement|concern|happiness|none",
      "dalle_prompt": "Detailed DALL-E prompt for generating this thumbnail",
      "ctr_potential": 7.5,
      "mobile_visibility_score": 8,
      "brand_consistent": true,
      "notes": "why this works"
    }}
  ],
  "best_concept_index": 0,
  "overall_ctr_potential": 7.5,
  "a_b_recommendation": "test concept 1 vs 2 for first 500 impressions",
  "brand_guidelines_followed": true
}}"""),
    ("human", """Title: {title}
Script excerpt: {script_excerpt}
Niche: {niche}
Channel brand colors: {brand_colors}
Target audience: {audience}
Emotional tone: {tone}
Generate {n_concepts} thumbnail concepts."""),
])


class ThumbnailPsychologyAgent(BaseAgent):
    agent_id = "thumbnail_psychology"
    layer = 3
    description = "Designs CTR-optimized thumbnails using psychology + DALL-E concept generation"
    tools = ["Thumbnail design engine", "DALL-E 3 image gen", "CTR predictor", "Color psychology"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("design_concepts", self._design_concepts)
        workflow.add_node("generate_images", self._generate_images)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "design_concepts")
        workflow.add_edge("design_concepts", "generate_images")
        workflow.add_edge("generate_images", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _design_concepts(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = THUMBNAIL_DESIGN_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "title": input_data.get("title", ""),
            "script_excerpt": input_data.get("script_text", "")[:300],
            "niche": input_data.get("niche", ""),
            "brand_colors": input_data.get("brand_colors", "red, white, black"),
            "audience": input_data.get("target_audience", "18-34 year olds"),
            "tone": input_data.get("tone", "energetic"),
            "n_concepts": input_data.get("n_concepts", 3),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            designs = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            designs = {"thumbnail_concepts": [], "error": "Parse failed"}

        state["output_data"]["designs"] = designs
        return state

    async def _generate_images(self, state: AgentState) -> AgentState:
        """Generate DALL-E images for each concept if requested."""
        designs = state["output_data"].get("designs", {})
        concepts = designs.get("thumbnail_concepts", [])
        input_data = state["input_data"]

        if not input_data.get("generate_images", False) or not concepts:
            state["output_data"]["generated_images"] = []
            return state

        from services.asset_service import asset_service
        generated = []
        for concept in concepts[:3]:  # Max 3 images to control cost
            dalle_prompt = concept.get("dalle_prompt", "")
            if dalle_prompt:
                result = await asset_service.generate_image_dalle(
                    f"YouTube thumbnail: {dalle_prompt}. 16:9 aspect ratio, eye-catching, high CTR design.",
                    concept.get("concept_id", 0),
                )
                concept["generated_url"] = result.get("url")
                concept["generation_cost"] = result.get("cost", 0.04)
                generated.append(result)

        state["output_data"]["generated_images"] = generated
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        designs = state["output_data"].get("designs", {})
        concepts = designs.get("thumbnail_concepts", [])
        overall_ctr = designs.get("overall_ctr_potential", 0)

        gate_passed = overall_ctr >= 7.0 and bool(concepts)

        state["output_data"]["final"] = {
            "concepts": concepts,
            "best_concept": concepts[designs.get("best_concept_index", 0)] if concepts else None,
            "overall_ctr_potential": overall_ctr,
            "a_b_recommendation": designs.get("a_b_recommendation", ""),
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": 7.0,
            "message": (
                f"Thumbnail gate PASSED: {overall_ctr:.1f}% CTR potential, {len(concepts)} concepts"
                if gate_passed
                else f"Thumbnail gate FAILED: CTR potential {overall_ctr:.1f}% < 7%"
            ),
        }
        state["quality_scores"]["ctr_potential"] = overall_ctr
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


thumbnail_psychology_agent = ThumbnailPsychologyAgent()
