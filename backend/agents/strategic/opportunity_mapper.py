"""
Agent #2: Opportunity Mapper Agent — Layer 1 (Market Intelligence)

Tworzy mape tematow: evergreen, trend-driven, seasonal, authority-building,
monetization-first, viral-first.
Generuje portfolio 50+ tematow startowych z priorytetyzacja.

Output: Topic Map z scoring per temat + content gap analysis
"""
from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
import json
import time

from agents.base import BaseAgent, AgentState


OPPORTUNITY_MAP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Jestes ekspertem content strategy na YouTube.
Tworzysz mape mozliwosci contentowych dla kanalu w danej niszy.

TYPY TEMATOW:
- evergreen: zawsze aktualne, dobry watch time, stabilny ruch
- trend_driven: aktualny trend, szybki wzrost wyswietlen
- seasonal: sezonowe piki (podatki w marcu, wakacje w czerwcu)
- authority_building: buduje autorytet kanalu, ciezsze do produkcji
- monetization_first: wysoki RPM, latwe do sponsorowania
- viral_first: wysoki potencjal viralnosci, hook-driven

ODPOWIEDZ JSON z lista 15-20 tematow:
{{
  "channel_niche": "...",
  "topics": [
    {{
      "title": "Tyul tematu",
      "type": "evergreen|trend_driven|seasonal|authority_building|monetization_first|viral_first",
      "priority_score": 0-100,
      "search_volume": "low|medium|high",
      "competition": "low|medium|high",
      "estimated_rpm": 0.0,
      "hook_potential": "low|medium|high",
      "series_potential": true/false,
      "notes": "Krotka nota strategiczna"
    }}
  ],
  "recommended_series": [
    {{"name": "Nazwa serii", "topics": ["temat1", "temat2"], "frequency": "weekly|biweekly"}}
  ],
  "content_pillars": ["filar1", "filar2", "filar3"]
}}"""),
    ("human", "Niche: {niche_name}\nAnalize niszy: {niche_analysis}\nJezyk: {language}"),
])


class OpportunityMapperAgent(BaseAgent):
    agent_id = "opportunity_mapper"
    layer = 1
    description = "Tworzy mape 50+ tematow: evergreen, trend-driven, seasonal, viral-first"
    tools = ["Niche Hunter output", "keyword tools", "Google Trends seasonality", "competitor content analysis"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("map_opportunities", self._map_opportunities)
        workflow.add_node("prioritize_topics", self._prioritize_topics)
        workflow.add_edge(START, "map_opportunities")
        workflow.add_edge("map_opportunities", "prioritize_topics")
        workflow.add_edge("prioritize_topics", END)
        return workflow.compile()

    async def _map_opportunities(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = OPPORTUNITY_MAP_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "niche_name": input_data.get("niche_name", ""),
            "niche_analysis": json.dumps(input_data.get("niche_analysis", {}), ensure_ascii=False),
            "language": input_data.get("language", "pl"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            opportunity_map = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            opportunity_map = {"error": "Parse failed", "raw": response.content[:500]}

        state["output_data"]["opportunity_map"] = opportunity_map
        return state

    async def _prioritize_topics(self, state: AgentState) -> AgentState:
        """Sort topics by priority score and add content calendar recommendations."""
        opportunity_map = state["output_data"].get("opportunity_map", {})
        topics = opportunity_map.get("topics", [])

        # Sort by priority score descending
        topics_sorted = sorted(topics, key=lambda t: t.get("priority_score", 0), reverse=True)
        opportunity_map["topics_ranked"] = topics_sorted
        opportunity_map["top_10_start_now"] = topics_sorted[:10]

        state["output_data"]["opportunity_map"] = opportunity_map
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


opportunity_mapper_agent = OpportunityMapperAgent()
