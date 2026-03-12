"""
Agent #1: Niche Hunter Agent — Layer 1 (Market Intelligence)

Analizuje nisze wedlug 7 czynnikow:
1. Popyt (search volume, trend)
2. Konkurencja (liczba kanalow, jaknosc)
3. Potencjal Watch Time
4. Potencjal Sponsoringu
5. Potencjal Afiliacji
6. Latwose Produkcji
7. Ryzyko Compliance

Quality Gate: Niche Score > 70/100
"""
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
import json
import time

from agents.base import BaseAgent, AgentState
from core.config import settings


NICHE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Jestes ekspertem od YouTube content strategy i analizy nisz.
Analizujesz nisze YouTube pod katem budowania dlugterminowego, monetyzowalnego kanalu.

KONTEKST 2026:
- YouTube zlikwidowal 16 kanalow za "inauthentic content" w stycniu 2026
- Polityka Inauthentic Content od 15.07.2025 — kara za template-driven, mass-produced content
- Kluczowe: wybieraj nisze gdzie mozna tworzyc ORYGINALNA wartosc, nie tylko repurposowac

SCORING SYSTEM (kazdy czynnik 0-100):
1. Demand Score: search volume + trend wzrostowy + audience size
2. Competition Score: 100 - poziom konkurencji (nizsza konkurencja = wyzszy score)
3. Watch Time Potential: czy temat sklania do dlugich filmow (>10min)?
4. Sponsor Potential: czy marki chca reklamowac sie w tej niszy?
5. Affiliate Potential: czy sa produkty afiliacyjne z dobra prowizja?
6. Production Feasibility: latwose produkcji bez twarzy (0=trudne, 100=latwe)
7. Compliance Risk: 100 - ryzyko copyright/compliance issues

Overall Score = srednia wazona: Demand(20%) + Competition(15%) + WatchTime(15%) + Sponsor(20%) + Affiliate(15%) + Production(10%) + Compliance(5%)

ODPOWIEDZ TYLKO JSON:
{{
  "name": "...",
  "category": "...",
  "demand_score": 0-100,
  "competition_score": 0-100,
  "watch_time_potential": 0-100,
  "sponsor_potential": 0-100,
  "affiliate_potential": 0-100,
  "production_feasibility": 0-100,
  "compliance_risk_score": 0-100,
  "overall_score": 0-100,
  "estimated_monthly_rpm": 0.0,
  "seasonality": "evergreen|seasonal|trend",
  "trend_direction": "up|stable|down",
  "top_competitors": ["kanal1", "kanal2", "kanal3"],
  "content_gaps": ["luka1", "luka2", "luka3"],
  "recommended_content_pillars": ["filar1", "filar2", "filar3"],
  "analysis_notes": "...",
  "quality_gate_passed": true/false
}}"""),
    ("human", """Analizuj nische: {niche_name}
Jezyk/kraj: {language}/{target_country}
Dodatkowy kontekst: {context}

Przygotuj pelna analize z scoring wszystkich 7 czynnikow."""),
])


class NicheHunterAgent(BaseAgent):
    agent_id = "niche_hunter"
    layer = 1
    description = "Analizuje nisze wedlug popytu, konkurencji, potencjalu RPM, sponsoringu i compliance risk"
    tools = ["YouTube Data API", "Google Trends API", "vidIQ data", "SimilarWeb"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("analyze_niche", self._analyze_niche)
        workflow.add_node("score_niche", self._score_niche)
        workflow.add_node("find_content_gaps", self._find_content_gaps)
        workflow.add_node("quality_gate", self._quality_gate_check)

        workflow.add_edge(START, "analyze_niche")
        workflow.add_edge("analyze_niche", "score_niche")
        workflow.add_edge("score_niche", "find_content_gaps")
        workflow.add_edge("find_content_gaps", "quality_gate")
        workflow.add_edge("quality_gate", END)

        return workflow.compile(checkpointer=self._checkpointer)

    async def _analyze_niche(self, state: AgentState) -> AgentState:
        """Step 1: LLM analysis of the niche."""
        input_data = state["input_data"]
        # MACRO tier — multi-factor strategic reasoning
        analysis_llm = self.get_routed_llm("niche_analysis", context_length=500)
        chain = NICHE_ANALYSIS_PROMPT | analysis_llm

        response = await chain.ainvoke({
            "niche_name": input_data.get("niche_name", ""),
            "language": input_data.get("language", "pl"),
            "target_country": input_data.get("target_country", "PL"),
            "context": input_data.get("context", "Brak dodatkowego kontekstu"),
        })

        try:
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            analysis = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            analysis = {"error": "Failed to parse LLM response", "raw": response.content}

        state["output_data"]["niche_analysis"] = analysis
        state["messages"].append(HumanMessage(content=f"Niche analyzed: {analysis.get('name', 'unknown')}"))
        return state

    async def _score_niche(self, state: AgentState) -> AgentState:
        """Step 2: Calculate weighted overall score."""
        analysis = state["output_data"].get("niche_analysis", {})

        if "error" not in analysis:
            weights = {
                "demand_score": 0.20,
                "competition_score": 0.15,
                "watch_time_potential": 0.15,
                "sponsor_potential": 0.20,
                "affiliate_potential": 0.15,
                "production_feasibility": 0.10,
                "compliance_risk_score": 0.05,
            }

            weighted_score = sum(
                analysis.get(key, 0) * weight
                for key, weight in weights.items()
            )
            analysis["overall_score"] = round(weighted_score, 1)

        state["quality_scores"]["niche_score"] = analysis.get("overall_score", 0)
        return state

    async def _find_content_gaps(self, state: AgentState) -> AgentState:
        """Step 3: Identify content gaps (topic opportunities)."""
        # In production: cross-reference with YouTube Data API for actual gaps
        analysis = state["output_data"].get("niche_analysis", {})
        if not analysis.get("content_gaps"):
            analysis["content_gaps"] = [
                f"{analysis.get('name', 'Nisza')} dla poczatkujacych",
                f"Zaawansowane strategie {analysis.get('name', '')}",
                f"Bledy w {analysis.get('name', '')} ktorych unikac",
            ]
        return state

    async def _quality_gate_check(self, state: AgentState) -> AgentState:
        """Step 4: Quality gate — Niche Score > 70."""
        score = state["quality_scores"].get("niche_score", 0)
        passed = score >= settings.min_niche_score

        state["output_data"]["quality_gate"] = {
            "passed": passed,
            "score": score,
            "threshold": settings.min_niche_score,
            "message": (
                f"Quality gate PASSED: Score {score} >= {settings.min_niche_score}"
                if passed
                else f"Quality gate FAILED: Score {score} < {settings.min_niche_score}. Wybierz inna nisza lub zoptymalizuj podejscie."
            ),
        }
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

        return {
            **final_state["output_data"],
            "agent_id": self.agent_id,
            "duration_seconds": round(duration, 2),
        }


# Singleton instance
niche_hunter_agent = NicheHunterAgent()
