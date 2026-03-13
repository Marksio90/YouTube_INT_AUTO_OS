"""
Agent #20: Monetization Readiness Agent — Layer 5 (Compliance)

Evaluates channel monetization eligibility, YPP status tracking,
revenue optimization, and channel health for monetization.

Quality Gate: YPP eligible check, RPM optimization score >= 70.
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


MONETIZATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube monetization expert. You assess channel readiness and optimize for revenue.

YPP REQUIREMENTS (2026):
Basic YPP:
- 500 subscribers
- 3 public uploads in 90 days
- 3,000 watch hours OR 3M Shorts views in 12 months
- Compliance with all policies

YPP Full (Monetization On):
- 1,000 subscribers
- 4,000 watch hours in 12 months OR 10M Shorts views in 90 days
- Two-step verification enabled
- No active Community Guidelines strikes
- Adherence to monetization policies

RPM OPTIMIZATION FACTORS:
1. Niche RPM benchmarks:
   - Finance/Investing: $15-35 RPM
   - Tech/Software: $8-20 RPM
   - Health/Medical: $10-25 RPM
   - Education: $5-12 RPM
   - Entertainment: $2-8 RPM
   - Gaming: $3-7 RPM

2. Geographic targeting (high CPM countries):
   - US, UK, CA, AU, NZ: Highest CPM
   - DE, FR, JP, KR: High CPM
   - SE, NO, CH: Very high CPM
   - BRICS countries: Lower CPM

3. Revenue streams beyond AdSense:
   - Channel memberships (>30K subs, need approval)
   - Super Thanks / Super Chat (live streams)
   - Merchandise shelf (Merch by Amazon, Spreadshop)
   - YouTube Premium revenue share
   - Brand deals (direct sponsors): Often 3-10x AdSense RPM
   - Affiliate marketing: High conversion with trust-built audience

4. Video optimization for revenue:
   - Longer videos (>8 min) = 2 mid-roll ad slots
   - >15 min = 3-5 mid-roll slots
   - High watch time percentage = more ad impressions
   - Upload frequency: 2-3x/week optimal for algorithm+revenue

RESPOND AS JSON:
{{
  "ypp_status": "not_eligible|basic_ypp|full_ypp|partner_plus",
  "ypp_progress": {{
    "subscribers": {{"current": 850, "required": 1000, "pct": 85}},
    "watch_hours": {{"current": 3200, "required": 4000, "pct": 80}},
    "estimated_days_to_eligible": 45
  }},
  "current_rpm_estimate": 8.50,
  "rpm_optimization_score": 72,
  "niche_rpm_benchmark": 12.0,
  "rpm_gap": 3.50,
  "revenue_streams": [
    {{"stream": "adsense", "status": "active|pending|not_available", "monthly_est": 150}},
    {{"stream": "memberships", "status": "not_available", "monthly_est": 0}},
    {{"stream": "brand_deals", "status": "possible", "monthly_est": 500}}
  ],
  "content_optimization_for_revenue": [
    "Videos average 6 min — extend to 8+ min for mid-roll ads",
    "Finance niche targets high CPM — current RPM below benchmark"
  ],
  "geographic_optimization": "Target US/UK audience — add English subtitles",
  "advertiser_safety_issues": [],
  "projected_monthly_revenue": {{
    "pessimistic": 120,
    "realistic": 280,
    "optimistic": 650
  }},
  "quality_gate_passed": true,
  "quality_gate_score": 72,
  "recommendations": ["..."]
}}"""),
    ("human", """Channel stats: {channel_stats}
Recent video metrics: {video_metrics}
Niche: {niche}
Current YPP status: {ypp_status}
Watch hours (12mo): {watch_hours}
Subscribers: {subscribers}"""),
])


class MonetizationReadinessAgent(BaseAgent):
    agent_id = "monetization_readiness"
    layer = 5
    description = "YPP eligibility check, RPM optimization, revenue stream planning. Gate: RPM score>=70"
    tools = ["YPP eligibility calculator", "RPM benchmarker", "Revenue forecaster", "Geo CPM optimizer"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("assess_ypp_status", self._assess_ypp_status)
        workflow.add_node("analyze_monetization", self._analyze_monetization)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "assess_ypp_status")
        workflow.add_edge("assess_ypp_status", "analyze_monetization")
        workflow.add_edge("analyze_monetization", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _assess_ypp_status(self, state: AgentState) -> AgentState:
        """Fetch latest channel stats for YPP assessment."""
        input_data = state["input_data"]
        channel_id = input_data.get("youtube_channel_id")

        if channel_id:
            try:
                from services.youtube_service import youtube_service
                stats = await youtube_service.get_channel_stats(channel_id)
                state["output_data"]["channel_stats"] = stats
            except Exception as e:
                self.logger.warning("Channel stats fetch failed", error=str(e))
                state["output_data"]["channel_stats"] = input_data.get("channel_stats", {})
        else:
            state["output_data"]["channel_stats"] = input_data.get("channel_stats", {})

        return state

    async def _analyze_monetization(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        channel_stats = state["output_data"].get("channel_stats", {})
        chain = MONETIZATION_PROMPT | self.get_routed_llm("check_ypp_policy")

        response = await chain.ainvoke({
            "channel_stats": json.dumps(channel_stats),
            "video_metrics": json.dumps(input_data.get("recent_video_metrics", {})),
            "niche": input_data.get("niche", ""),
            "ypp_status": input_data.get("ypp_status", "unknown"),
            "watch_hours": channel_stats.get("watch_hours_12mo", input_data.get("watch_hours", 0)),
            "subscribers": channel_stats.get("subscriber_count", input_data.get("subscribers", 0)),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            analysis = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            analysis = {
                "ypp_status": "not_eligible",
                "rpm_optimization_score": 50,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["monetization_analysis"] = analysis
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        analysis = state["output_data"].get("monetization_analysis", {})
        rpm_score = analysis.get("rpm_optimization_score", 0)
        gate_passed = rpm_score >= 70

        state["output_data"]["final"] = {
            "ypp_status": analysis.get("ypp_status", "not_eligible"),
            "ypp_progress": analysis.get("ypp_progress", {}),
            "current_rpm_estimate": analysis.get("current_rpm_estimate", 0),
            "rpm_optimization_score": rpm_score,
            "niche_rpm_benchmark": analysis.get("niche_rpm_benchmark", 0),
            "revenue_streams": analysis.get("revenue_streams", []),
            "projected_monthly_revenue": analysis.get("projected_monthly_revenue", {}),
            "recommendations": analysis.get("recommendations", []),
            "content_optimization_for_revenue": analysis.get("content_optimization_for_revenue", []),
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": 70,
            "message": (
                f"Monetization gate PASSED: RPM score {rpm_score}/100, status: {analysis.get('ypp_status')}"
                if gate_passed
                else f"Monetization gate FAILED: RPM score {rpm_score}/100 < 70"
            ),
        }
        state["quality_scores"]["rpm_optimization_score"] = float(rpm_score)
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


monetization_readiness_agent = MonetizationReadinessAgent()
