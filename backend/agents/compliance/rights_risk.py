"""
Agent #19: Rights & Risk Agent — Layer 5 (Compliance)

Checks content for copyright, music licensing, fair use,
privacy violations, defamation risk, and advertiser safety.

Quality Gate: No copyright strikes risk, AdSense friendly >= 80/100.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


RIGHTS_RISK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a digital media rights and risk compliance attorney specializing in YouTube content.

RISK ASSESSMENT FRAMEWORK:

1. COPYRIGHT RISK:
- Script references to copyrighted works (books, songs, films, TV shows)
- Clips/screenshots from copyrighted material
- Music usage without license
- Fair use: commentary/criticism/education may be OK, but risky

2. MUSIC LICENSING:
- YouTube Audio Library: SAFE (free to use)
- Creative Commons (CC0, CC-BY): SAFE
- Licensed royalty-free (Epidemic Sound, Artlist): SAFE with subscription
- Popular music without license: HIGH RISK — Content ID strike
- Classical/pre-1928: Public domain SAFE

3. PRIVACY & DEFAMATION:
- Named real people: Check defamation risk
- Medical/financial advice disclaimers required
- Personal data exposure: GDPR/CCPA risk
- "Deep fake" likeness: New YouTube policy (2026)

4. ADVERTISER SAFETY (BRAND SAFETY):
- Yellow dollar sign ($): Limited monetization
- Violence/gore: Demonetized
- Adult content: Age-restricted
- Controversial topics: Limited ads
- Profanity: Limited reach

YOUTUBE COMMUNITY GUIDELINES RED FLAGS:
- Dangerous challenges
- Misleading health/financial claims
- Coordinated inauthentic behavior
- Hate speech / harassment

RESPOND AS JSON:
{{
  "copyright_risk": "none|low|medium|high|critical",
  "copyright_issues": ["list of specific issues"],
  "music_risk": "none|low|medium|high",
  "music_recommendations": ["Use YouTube Audio Library for background music"],
  "privacy_risk": "none|low|medium|high",
  "privacy_issues": [],
  "defamation_risk": "none|low|medium|high",
  "defamation_issues": [],
  "advertiser_safety_score": 85,
  "monetization_status": "full|limited|age_restricted|demonetized",
  "disclaimers_needed": ["This is not financial advice"],
  "community_guidelines_risk": "none|low|medium|high",
  "community_guidelines_issues": [],
  "fair_use_analysis": "...",
  "overall_risk_level": "green|yellow|red|critical",
  "quality_gate_passed": true,
  "action_items": ["..."],
  "notes": "..."
}}"""),
    ("human", """Title: {title}
Script: {script_excerpt}
Niche: {niche}
Music planned: {music_planned}
People mentioned: {people_mentioned}
Sources cited: {sources}"""),
])


class RightsRiskAgent(BaseAgent):
    agent_id = "rights_risk"
    layer = 5
    description = "Copyright, music licensing, privacy, defamation, advertiser safety check"
    tools = ["Copyright scanner", "Music license checker", "Defamation risk analyzer", "AdSense safety scorer"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("scan_content", self._scan_content)
        workflow.add_node("music_check", self._music_check)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "scan_content")
        workflow.add_edge("scan_content", "music_check")
        workflow.add_edge("music_check", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _scan_content(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = RIGHTS_RISK_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "title": input_data.get("title", ""),
            "script_excerpt": input_data.get("script_text", "")[:3000],
            "niche": input_data.get("niche", ""),
            "music_planned": input_data.get("music_planned", "royalty-free background music"),
            "people_mentioned": ", ".join(input_data.get("people_mentioned", [])),
            "sources": ", ".join(input_data.get("sources_cited", [])),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            risk_report = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            risk_report = {
                "overall_risk_level": "yellow",
                "advertiser_safety_score": 70,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["risk_report"] = risk_report
        return state

    async def _music_check(self, state: AgentState) -> AgentState:
        """Additional structured music license check."""
        input_data = state["input_data"]
        music_tracks = input_data.get("music_tracks", [])

        licensed_sources = {"youtube_audio_library", "epidemic_sound", "artlist", "musicbed", "cc0", "public_domain"}
        risky_tracks = []

        for track in music_tracks:
            source = track.get("source", "").lower().replace(" ", "_")
            if source not in licensed_sources:
                risky_tracks.append(track)

        state["output_data"]["music_check"] = {
            "total_tracks": len(music_tracks),
            "risky_tracks": risky_tracks,
            "safe": len(risky_tracks) == 0,
        }
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        risk_report = state["output_data"].get("risk_report", {})
        music_check = state["output_data"].get("music_check", {})

        overall_risk = risk_report.get("overall_risk_level", "yellow")
        safety_score = risk_report.get("advertiser_safety_score", 70)
        music_safe = music_check.get("safe", True)

        gate_passed = (
            overall_risk in ["green", "yellow"]
            and safety_score >= 80
            and music_safe
            and risk_report.get("copyright_risk") not in ["high", "critical"]
        )

        state["output_data"]["final"] = {
            "overall_risk_level": overall_risk,
            "advertiser_safety_score": safety_score,
            "monetization_status": risk_report.get("monetization_status", "full"),
            "copyright_risk": risk_report.get("copyright_risk", "none"),
            "music_risk": risk_report.get("music_risk", "none"),
            "privacy_risk": risk_report.get("privacy_risk", "none"),
            "disclaimers_needed": risk_report.get("disclaimers_needed", []),
            "action_items": risk_report.get("action_items", []),
            "music_check": music_check,
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": {"safety_score": 80, "risk_level": "yellow"},
            "message": (
                f"Rights gate PASSED: {overall_risk} risk, AdSense {safety_score}/100"
                if gate_passed
                else f"Rights gate FAILED: {overall_risk} risk or score {safety_score}/100 < 80"
            ),
        }
        state["quality_scores"]["advertiser_safety"] = float(safety_score)
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


rights_risk_agent = RightsRiskAgent()
