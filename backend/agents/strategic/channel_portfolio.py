"""
Agent #5: Channel Portfolio Agent — Layer 1 (Strategic)

Manages multi-channel strategy for creators running multiple YouTube channels.
Analyzes cross-channel cannibalization, resource allocation, and synergies.

Also handles channel brand consistency and portfolio-level compliance monitoring.
Quality Gate: Portfolio diversity score >= 70, no cannibalization > 30%.
"""
import json
import time
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState


PORTFOLIO_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a multi-channel YouTube portfolio strategist. You optimize channel networks for maximum total reach and revenue.

PORTFOLIO STRATEGY FRAMEWORKS:

1. AUDIENCE CANNIBALIZATION:
- Two channels competing for same audience = reduced growth for both
- Acceptable overlap: <30% shared audience (measure by niche similarity)
- Solution: Differentiate positioning, audience segment, or content depth

2. CHANNEL SYNERGY OPPORTUNITIES:
- Channel A audience likely interested in Channel B content
- Cross-promotion: mention Channel B at relevant moments in Channel A
- Content repurposing: Long-form Channel A → Shorts Channel B
- Shared production resources: Same thumbnail template, TTS voice

3. PORTFOLIO RESOURCE ALLOCATION:
- ROI-first: Allocate 60% resources to highest-performing channel
- Growth mode: Allocate 30% to fastest-growing channel
- Experiment: 10% to new/test channel
- Sunset: Consider pausing channels below 20th percentile for 6+ months

4. RISK DISTRIBUTION:
- No single channel > 60% of total revenue (concentration risk)
- Different niches = protection against niche-specific policy changes
- Multiple ad categories = protection against CPM fluctuations

5. BRAND ARCHITECTURE:
- Branded house: All channels share master brand identity
- House of brands: Each channel has independent brand
- Hybrid: Master brand + sub-brands

RESPOND AS JSON:
{{
  "portfolio_health": "excellent|good|needs_attention|critical",
  "total_channels": 3,
  "portfolio_diversity_score": 78,
  "cannibalization_matrix": [
    {{"channel_a": "ch1", "channel_b": "ch2", "overlap_pct": 22, "risk": "low"}}
  ],
  "synergy_opportunities": [
    {{
      "type": "cross_promotion|content_repurposing|shared_resources",
      "channels": ["ch1", "ch2"],
      "estimated_lift_pct": 15,
      "action": "Description of action"
    }}
  ],
  "resource_allocation": [
    {{"channel_id": "ch1", "recommended_pct": 60, "rationale": "..."}}
  ],
  "brand_architecture": "branded_house|house_of_brands|hybrid",
  "risk_flags": [],
  "channels_to_prioritize": ["ch1"],
  "channels_to_pause": [],
  "projected_portfolio_growth_pct": 35,
  "quality_gate_passed": true,
  "recommendations": ["..."]
}}"""),
    ("human", """Channels in portfolio: {channels}
Channel metrics: {metrics}
Current resource allocation: {current_allocation}
Business goals: {goals}"""),
])


class ChannelPortfolioAgent(BaseAgent):
    agent_id = "channel_portfolio"
    layer = 1
    description = "Multi-channel portfolio strategy: cannibalization analysis, synergies, resource allocation"
    tools = ["Audience overlap analyzer", "Portfolio ROI calculator", "Cross-promo opportunity finder", "Resource allocator"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze_portfolio", self._analyze_portfolio)
        workflow.add_node("identify_synergies", self._identify_synergies)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "analyze_portfolio")
        workflow.add_edge("analyze_portfolio", "identify_synergies")
        workflow.add_edge("identify_synergies", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    async def _analyze_portfolio(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = PORTFOLIO_ANALYSIS_PROMPT | self.get_routed_llm("channel_strategy")

        response = await chain.ainvoke({
            "channels": json.dumps(input_data.get("channels", [])),
            "metrics": json.dumps(input_data.get("channel_metrics", {})),
            "current_allocation": json.dumps(input_data.get("current_resource_allocation", {})),
            "goals": input_data.get("business_goals", "Maximize total channel revenue and subscriber growth"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            portfolio_analysis = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            portfolio_analysis = {
                "portfolio_diversity_score": 60,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["portfolio_analysis"] = portfolio_analysis
        return state

    async def _identify_synergies(self, state: AgentState) -> AgentState:
        """Extract and rank synergy opportunities by estimated lift."""
        analysis = state["output_data"].get("portfolio_analysis", {})
        synergies = analysis.get("synergy_opportunities", [])

        # Sort by estimated lift
        synergies_sorted = sorted(synergies, key=lambda s: s.get("estimated_lift_pct", 0), reverse=True)
        state["output_data"]["ranked_synergies"] = synergies_sorted[:5]  # Top 5
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        analysis = state["output_data"].get("portfolio_analysis", {})
        diversity_score = analysis.get("portfolio_diversity_score", 0)

        # Check cannibalization — any pair with >30% overlap?
        cannibalization_matrix = analysis.get("cannibalization_matrix", [])
        max_overlap = max((c.get("overlap_pct", 0) for c in cannibalization_matrix), default=0)

        gate_passed = diversity_score >= 70 and max_overlap <= 30

        state["output_data"]["final"] = {
            "portfolio_health": analysis.get("portfolio_health", "needs_attention"),
            "portfolio_diversity_score": diversity_score,
            "cannibalization_matrix": cannibalization_matrix,
            "max_overlap_pct": max_overlap,
            "synergy_opportunities": state["output_data"].get("ranked_synergies", []),
            "resource_allocation": analysis.get("resource_allocation", []),
            "channels_to_prioritize": analysis.get("channels_to_prioritize", []),
            "channels_to_pause": analysis.get("channels_to_pause", []),
            "projected_growth_pct": analysis.get("projected_portfolio_growth_pct", 0),
            "recommendations": analysis.get("recommendations", []),
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": {"diversity": 70, "max_overlap": 30},
            "message": (
                f"Portfolio gate PASSED: diversity {diversity_score}/100, max overlap {max_overlap}%"
                if gate_passed
                else f"Portfolio gate FAILED: diversity {diversity_score}/100 < 70 or overlap {max_overlap}% > 30%"
            ),
        }
        state["quality_scores"]["portfolio_diversity"] = float(diversity_score)
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


channel_portfolio_agent = ChannelPortfolioAgent()
