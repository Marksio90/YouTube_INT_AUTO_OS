"""
Agent #15: Watch Time Forensics — Layer 4 (Growth)

Post-publish analytics deep dive. Analyzes YouTube Analytics data
to identify exact retention drop points, audience segments, and
provide actionable recommendations for next video.

Triggered at: 2h, 24h, 72h, 7d, 28d post-publish checkpoints.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


FORENSICS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube analytics forensics expert. You diagnose performance and prescribe fixes.

ANALYTICS INTERPRETATION GUIDE:

RETENTION BENCHMARKS (2026):
- 0-30s: >70% = excellent, 50-70% = good, <50% = hook failure
- Average view duration: >40% = excellent, 25-40% = average, <25% = poor
- Click-through rate: >6% = excellent, 3-6% = good, <3% = poor
- Impressions → views conversion: >5% = excellent

RETENTION DROP POINT ANALYSIS:
- Drop at :30 = Intro too slow, no value delivery
- Drop at 1:00-2:00 = Failed to fulfill hook promise
- Drop at 50% mark = Mid-video momentum lost, no callback
- Drop at 80% = Weak call-to-action, no reason to stay
- Gradual decline = Content too dense/boring

TRAFFIC SOURCE INSIGHTS:
- YouTube Search > 30% = SEO working, optimize titles/descriptions
- Browse Features > 40% = Algorithm pushing video, thumbnail working
- External > 20% = Good social distribution
- Suggested Videos > 25% = Good session contribution

AUDIENCE RETENTION PATTERNS:
- Re-watches: High re-watch at specific timestamp = very valuable content
- Shares: High shares per view = strong emotional resonance
- Comments/Like ratio: >1% comments = highly engaging topic

RESPOND AS JSON:
{{
  "performance_grade": "A|B|C|D|F",
  "overall_health": "excellent|good|average|poor|critical",
  "key_metrics": {{
    "avg_view_duration_pct": 45.2,
    "ctr_pct": 5.8,
    "total_views": 12500,
    "watch_time_hours": 940
  }},
  "retention_analysis": {{
    "hook_retention_pct": 72,
    "midpoint_retention_pct": 52,
    "end_retention_pct": 35,
    "critical_drops": [
      {{"timestamp_seconds": 95, "drop_pct": 18, "diagnosis": "...", "fix": "..."}}
    ]
  }},
  "traffic_breakdown": {{
    "search_pct": 35,
    "browse_pct": 28,
    "suggested_pct": 22,
    "external_pct": 15
  }},
  "audience_insights": {{
    "top_geographies": ["US", "UK", "CA"],
    "peak_viewing_times": ["18:00-22:00 EST", "Saturdays"],
    "device_breakdown": {{"mobile": 68, "desktop": 25, "tv": 7}}
  }},
  "content_recommendations": [
    "Make intro 30s shorter",
    "Add pattern interrupt at 1:45",
    "Next video should cover [related topic]"
  ],
  "seo_opportunities": ["..."],
  "next_video_hooks": ["Hook idea based on performance data"],
  "alert_level": "none|info|warning|critical",
  "alert_message": "..."
}}"""),
    ("human", """Video: {title}
Published: {published_at}
Analytics checkpoint: {checkpoint}

Retention data: {retention_data}
Traffic sources: {traffic_sources}
Key metrics: {key_metrics}
Audience data: {audience_data}"""),
])


class WatchTimeForensicsAgent(BaseAgent):
    agent_id = "watch_time_forensics"
    layer = 4
    description = "Post-publish analytics deep dive at 2h/24h/72h/7d/28d checkpoints"
    tools = ["YouTube Analytics API", "Retention curve analyzer", "Traffic source breakdown", "Audience segmenter"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("fetch_analytics", self._fetch_analytics)
        workflow.add_node("run_forensics", self._run_forensics)
        workflow.add_node("generate_recommendations", self._generate_recommendations)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "fetch_analytics")
        workflow.add_edge("fetch_analytics", "run_forensics")
        workflow.add_edge("run_forensics", "generate_recommendations")
        workflow.add_edge("generate_recommendations", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _fetch_analytics(self, state: AgentState) -> AgentState:
        """Fetch real analytics from YouTube Data API."""
        input_data = state["input_data"]
        video_id = input_data.get("youtube_video_id")

        if not video_id:
            state["output_data"]["analytics"] = {"error": "No video_id provided"}
            return state

        try:
            from services.youtube_service import youtube_service
            analytics = await youtube_service.get_video_analytics(video_id)
            state["output_data"]["analytics"] = analytics
        except Exception as e:
            self.logger.warning("Analytics fetch failed", error=str(e))
            state["output_data"]["analytics"] = input_data.get("analytics_data", {})

        return state

    async def _run_forensics(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        analytics = state["output_data"].get("analytics", {})
        chain = FORENSICS_PROMPT | self.get_routed_llm("score_retention")

        response = await chain.ainvoke({
            "title": input_data.get("title", ""),
            "published_at": input_data.get("published_at", ""),
            "checkpoint": input_data.get("checkpoint", "24h"),
            "retention_data": json.dumps(analytics.get("retention_curve", [])),
            "traffic_sources": json.dumps(analytics.get("traffic_sources", {})),
            "key_metrics": json.dumps(analytics.get("metrics", {})),
            "audience_data": json.dumps(analytics.get("audience", {})),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            forensics = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            forensics = {"performance_grade": "C", "error": "Parse failed"}

        state["output_data"]["forensics"] = forensics
        return state

    async def _generate_recommendations(self, state: AgentState) -> AgentState:
        """Compile actionable next steps."""
        forensics = state["output_data"].get("forensics", {})
        recs = forensics.get("content_recommendations", [])
        seo_ops = forensics.get("seo_opportunities", [])

        state["output_data"]["action_items"] = {
            "immediate": [r for r in recs if "title" in r.lower() or "thumbnail" in r.lower()],
            "next_video": forensics.get("next_video_hooks", []),
            "seo": seo_ops,
            "all": recs + seo_ops,
        }
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        forensics = state["output_data"].get("forensics", {})
        action_items = state["output_data"].get("action_items", {})

        state["output_data"]["final"] = {
            "performance_grade": forensics.get("performance_grade", "C"),
            "overall_health": forensics.get("overall_health", "average"),
            "key_metrics": forensics.get("key_metrics", {}),
            "retention_analysis": forensics.get("retention_analysis", {}),
            "traffic_breakdown": forensics.get("traffic_breakdown", {}),
            "audience_insights": forensics.get("audience_insights", {}),
            "action_items": action_items,
            "alert_level": forensics.get("alert_level", "none"),
            "alert_message": forensics.get("alert_message", ""),
            "quality_gate_passed": True,  # Analysis always passes; grade is the metric
            "message": f"Forensics complete: Grade {forensics.get('performance_grade', 'C')} — {forensics.get('overall_health', 'average')}",
        }
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


watch_time_forensics_agent = WatchTimeForensicsAgent()
