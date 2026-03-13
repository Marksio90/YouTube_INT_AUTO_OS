"""
Agent #3: Competitive Deconstruction Agent — Layer 1 (Market Intelligence)

Rozbiera top kanaly konkurencji:
- Dlugosc filmow, tempo montazu
- Typy hookow
- Slownictwo tytulow i wzorce CTR
- Rytm miniatur i schematy retencji
- Wzorce publikacji

Output: Competitive Matrix z actionable insights per kanal
"""
from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
import json
import time

from agents.base import BaseAgent, AgentState


COMPETITIVE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Jestes ekspertem od analizy konkurencji YouTube.
Analizujesz top kanaly w niszy i wyciagasz actionable insights.

Analizuj:
1. Formaty filmow (dlugosc, tempo, struktura)
2. Typy hookow (pierwsze 30 sekund)
3. Wzorce tytulow (kluczsowe slowa, struktura, emocje)
4. Miniatury (kolory, tekst, emocje, kontrast)
5. Wzorce publikacji (czestotliwosc, pory)
6. Strategie SEO (tagi, opisy)
7. Luki — co konkurencja POMIJA

ODPOWIEDZ JSON:
{{
  "niche": "...",
  "competitors_analyzed": ["kanal1", "kanal2"],
  "competitive_matrix": {{
    "avg_video_length_minutes": 0.0,
    "dominant_hook_types": ["typ1", "typ2"],
    "title_patterns": ["pattern1", "pattern2"],
    "thumbnail_styles": ["styl1", "styl2"],
    "upload_frequency": "X filmow tygodniowo",
    "avg_views_per_video": 0,
    "avg_ctr_estimated": "X%"
  }},
  "differentiation_opportunities": ["okazja1", "okazja2", "okazja3"],
  "hooks_to_steal": ["hook1", "hook2"],
  "gaps_in_market": ["luka1", "luka2"],
  "recommended_positioning": "Twoje unikalne pozycjonowanie wzgledem konkurencji"
}}"""),
    ("human", "Nisza: {niche_name}\nTop kanaly do analizy: {competitor_channels}\nJezyk: {language}"),
])


class CompetitiveDeconstructionAgent(BaseAgent):
    agent_id = "competitive_deconstruction"
    layer = 1
    description = "Rozbiera top kanaly: dlugosc, hooks, typy tytulow, rytm miniatur, wzorce retencji"
    tools = ["YouTube Analytics API", "competitor channel data", "video metadata scraping"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze_competitors", self._analyze_competitors)
        workflow.add_node("extract_insights", self._extract_insights)
        workflow.add_edge(START, "analyze_competitors")
        workflow.add_edge("analyze_competitors", "extract_insights")
        workflow.add_edge("extract_insights", END)
        return workflow.compile()

    async def _analyze_competitors(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = COMPETITIVE_ANALYSIS_PROMPT | self.get_routed_llm("competitive_deconstruction")

        response = await chain.ainvoke({
            "niche_name": input_data.get("niche_name", ""),
            "competitor_channels": ", ".join(input_data.get("competitor_channels", [])),
            "language": input_data.get("language", "pl"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            analysis = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            analysis = {"error": "Parse failed"}

        state["output_data"]["competitive_analysis"] = analysis
        return state

    async def _extract_insights(self, state: AgentState) -> AgentState:
        """Summarize key actionable insights."""
        analysis = state["output_data"].get("competitive_analysis", {})
        state["output_data"]["key_insights"] = {
            "gaps": analysis.get("gaps_in_market", []),
            "positioning": analysis.get("recommended_positioning", ""),
            "hooks_to_adapt": analysis.get("hooks_to_steal", []),
            "differentiation": analysis.get("differentiation_opportunities", []),
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


competitive_deconstruction_agent = CompetitiveDeconstructionAgent()
