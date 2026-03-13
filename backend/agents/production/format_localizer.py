"""
Agent #11: Format Localizer — Layer 3 (Production)

Adapts video format and style for different markets/languages.
Handles cultural adaptation, length optimization per platform,
and multi-language script adaptation.

Platforms: YouTube (long), YouTube Shorts (60s), TikTok (90s), Instagram Reels (30s).
Quality Gate: Format compliance >= 90%, cultural sensitivity check passed.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


FORMAT_ADAPTATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a multi-platform content localization expert. You adapt YouTube content for different platforms and markets.

PLATFORM REQUIREMENTS:
- YouTube Long: 8-20 min optimal, 16:9, any topic depth
- YouTube Shorts: 15-60 sec, 9:16 vertical, hook in first 3s, loop-friendly
- TikTok: 15-90 sec, 9:16, trend hooks, duet-friendly
- Instagram Reels: 15-30 sec, 9:16, visual-first, minimal text

MARKET LOCALIZATION FACTORS:
- Language: Direct translation vs. cultural adaptation
- Humor: Region-specific (Polish vs. American vs. UK humor differs)
- Examples/analogies: Replace US-centric references with local ones
- Currency/units: Convert to local (USD→PLN, miles→km)
- Cultural sensitivity: Religious, political, social taboos vary

POLISH MARKET SPECIFICS:
- Formal/informal register: "Pan/Pani" (formal) vs "Ty" (informal)
- Slang evolution: Mix of local Polish + English-adopted terms OK
- Cultural references: Prefer Polish examples over American
- Length preference: Polish audience tolerates longer explanations

SCRIPT SHORTENING TECHNIQUES:
- Remove filler phrases ("So basically", "You know what I mean")
- Compress examples to one instead of three
- Cut repeated points
- Convert explanations to visual overlays (noted in script)

RESPOND AS JSON:
{{
  "adapted_formats": [
    {{
      "platform": "youtube_shorts",
      "duration_seconds": 58,
      "adapted_script": "Full adapted script for this platform",
      "aspect_ratio": "9:16",
      "hook": "First 3 seconds hook text",
      "cta": "End call to action",
      "visual_notes": ["Close-up of results", "Text overlay for key stat"],
      "format_compliance_score": 92
    }}
  ],
  "localization_changes": [
    "Changed '$500' to '2000 zł'",
    "Replaced baseball analogy with football analogy"
  ],
  "cultural_sensitivity_passed": true,
  "cultural_flags": [],
  "register_recommendation": "informal",
  "quality_gate_passed": true,
  "quality_gate_score": 91
}}"""),
    ("human", """Original script: {script_text}
Target platforms: {platforms}
Original language: {source_language}
Target markets: {target_markets}
Niche: {niche}
Original duration: {duration}s"""),
])


class FormatLocalizerAgent(BaseAgent):
    agent_id = "format_localizer"
    layer = 3
    description = "Multi-platform format adaptation (Shorts/TikTok/Reels) + cultural localization"
    tools = ["Platform format library", "Script shortener", "Cultural sensitivity checker", "Translation assistant"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("adapt_formats", self._adapt_formats)
        workflow.add_node("check_cultural_sensitivity", self._check_cultural_sensitivity)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "adapt_formats")
        workflow.add_edge("adapt_formats", "check_cultural_sensitivity")
        workflow.add_edge("check_cultural_sensitivity", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _adapt_formats(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = FORMAT_ADAPTATION_PROMPT | self.get_routed_llm("localize_format")

        script_text = input_data.get("script_text", "")
        word_count = len(script_text.split())
        duration_est = int(word_count / 130 * 60)

        response = await chain.ainvoke({
            "script_text": script_text[:4000],
            "platforms": ", ".join(input_data.get("platforms", ["youtube_shorts"])),
            "source_language": input_data.get("source_language", "Polish"),
            "target_markets": ", ".join(input_data.get("target_markets", ["PL"])),
            "niche": input_data.get("niche", ""),
            "duration": duration_est,
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            adaptation = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            adaptation = {
                "adapted_formats": [],
                "cultural_sensitivity_passed": True,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["adaptation"] = adaptation
        return state

    async def _check_cultural_sensitivity(self, state: AgentState) -> AgentState:
        """Flag any cultural sensitivity issues."""
        adaptation = state["output_data"].get("adaptation", {})
        flags = adaptation.get("cultural_flags", [])
        state["output_data"]["sensitivity_check"] = {
            "passed": len(flags) == 0,
            "flags": flags,
        }
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        adaptation = state["output_data"].get("adaptation", {})
        formats = adaptation.get("adapted_formats", [])
        sensitivity = state["output_data"].get("sensitivity_check", {})

        avg_compliance = (
            sum(f.get("format_compliance_score", 0) for f in formats) / len(formats)
            if formats else 0
        )
        gate_passed = avg_compliance >= 90 and sensitivity.get("passed", True)

        state["output_data"]["final"] = {
            "adapted_formats": formats,
            "localization_changes": adaptation.get("localization_changes", []),
            "cultural_sensitivity_passed": sensitivity.get("passed", True),
            "cultural_flags": sensitivity.get("flags", []),
            "avg_format_compliance": avg_compliance,
            "register_recommendation": adaptation.get("register_recommendation", "informal"),
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": 90,
            "message": (
                f"Format gate PASSED: {avg_compliance:.1f}% compliance, {len(formats)} formats adapted"
                if gate_passed
                else f"Format gate FAILED: compliance {avg_compliance:.1f}% < 90%"
            ),
        }
        state["quality_scores"]["format_compliance"] = avg_compliance
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


format_localizer_agent = FormatLocalizerAgent()
