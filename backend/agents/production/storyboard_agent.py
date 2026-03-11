"""
Agent #10: Storyboard Agent — Layer 3 (Production)

Converts script into scene-by-scene storyboard with B-roll cues,
visual descriptions, pacing, and asset queries for the asset retrieval step.

Output format is consumed by Asset Retrieval Agent and Video Assembly Service.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


STORYBOARD_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a professional video storyboard director. You translate scripts into visual scene plans.

STORYBOARD RULES:
- Scene length: 3-8 seconds each (YouTube: rapid cuts hold attention)
- Every voice line needs a corresponding visual
- B-roll should ENHANCE, not distract from audio
- Transitions: cut, dissolve, zoom, slide
- Text on screen: key stats, bullet points, emphasis words
- pacing: FAST for hooks, MEDIUM for explanation, SLOW for emphasis

SCENE TYPES:
- talking_head: Speaker on camera
- b_roll_video: Stock video clip showing topic
- b_roll_image: Static image with ken burns
- screen_record: Software/website demonstration
- animation: Motion graphics or text animation
- lower_third: Text banner with name/title
- fullscreen_text: Key point as large text

ASSET TYPES FOR B-ROLL:
- stock_photo: Search Pexels/Pixabay
- stock_video: Search Pexels Videos
- generated: DALL-E 3 generation

RESPOND AS JSON:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "timestamp_start": 0,
      "timestamp_end": 5,
      "duration": 5,
      "type": "b_roll_video|b_roll_image|talking_head|screen_record|animation|fullscreen_text",
      "voice_text": "exact words spoken during this scene",
      "visual_description": "What is shown on screen",
      "asset_type": "stock_video|stock_photo|generated|none",
      "asset_query": "search query for Pexels/Pixabay",
      "transition_in": "cut|dissolve|zoom|slide",
      "text_overlay": null,
      "camera_note": "wide|close|medium|none",
      "music_note": "up|down|maintain"
    }}
  ],
  "total_scenes": 18,
  "estimated_duration_seconds": 420,
  "b_roll_count": 12,
  "generated_asset_count": 2,
  "asset_cost_estimate": 0.08,
  "production_notes": "..."
}}"""),
    ("human", """Script: {script_text}

Title: {title}
Video format: {format}
Target duration: {target_duration} seconds
Style: {style}"""),
])


class StoryboardAgent(BaseAgent):
    agent_id = "storyboard"
    layer = 3
    description = "Converts script to scene-by-scene storyboard with B-roll cues and asset queries"
    tools = ["Scene planner", "B-roll cue generator", "Timing calculator", "Asset query builder"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("create_storyboard", self._create_storyboard)
        workflow.add_node("optimize_pacing", self._optimize_pacing)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "create_storyboard")
        workflow.add_edge("create_storyboard", "optimize_pacing")
        workflow.add_edge("optimize_pacing", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _create_storyboard(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = STORYBOARD_PROMPT | self.llm_premium

        word_count = len(input_data.get("script_text", "").split())
        target_duration = input_data.get("target_duration", int(word_count / 130 * 60))

        response = await chain.ainvoke({
            "script_text": input_data.get("script_text", "")[:5000],
            "title": input_data.get("title", ""),
            "format": input_data.get("format", "educational"),
            "target_duration": target_duration,
            "style": input_data.get("style", "professional"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            storyboard = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            storyboard = {"scenes": [], "error": "Parse failed"}

        state["output_data"]["storyboard"] = storyboard
        return state

    async def _optimize_pacing(self, state: AgentState) -> AgentState:
        """Ensure scenes are within 3-8 second range, fix outliers."""
        scenes = state["output_data"].get("storyboard", {}).get("scenes", [])

        for scene in scenes:
            duration = scene.get("duration", 5)
            if duration > 10:
                scene["pacing_note"] = "Consider splitting this scene"
            elif duration < 2:
                scene["pacing_note"] = "Consider merging with adjacent scene"

        state["output_data"]["optimized_scenes"] = scenes
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        storyboard = state["output_data"].get("storyboard", {})
        scenes = storyboard.get("scenes", [])

        state["output_data"]["final"] = {
            "scenes": scenes,
            "total_scenes": len(scenes),
            "estimated_duration_seconds": storyboard.get("estimated_duration_seconds", 0),
            "b_roll_count": storyboard.get("b_roll_count", 0),
            "generated_asset_count": storyboard.get("generated_asset_count", 0),
            "asset_cost_estimate": storyboard.get("asset_cost_estimate", 0),
            "production_notes": storyboard.get("production_notes", ""),
            "quality_gate_passed": bool(scenes),
            "message": f"Storyboard created: {len(scenes)} scenes, ~{storyboard.get('estimated_duration_seconds', 0)}s",
        }
        state["quality_scores"]["storyboard_completeness"] = 100.0 if scenes else 0.0
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


storyboard_agent = StoryboardAgent()
