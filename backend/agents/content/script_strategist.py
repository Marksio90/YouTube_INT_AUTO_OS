"""
Agent #5: Script Strategist Agent — Layer 2 (Content Design Engine)

Na bazie briefu ustala:
- Glowna obietnice filmu
- Luke informacyjna (czego widzowie jeszcze nie wiedza)
- Glowna emocje
- Strukture narracyjna
- Momenty utraty uwagi i miejsca na reset ciekawosci

Odpowiada 6-czesciowej strukturze z Modulu II kursu.
Quality Gate: Naturalnosc > 8/10, Hook Score > 8/10
"""
from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
import json
import time

from agents.base import BaseAgent, AgentState
from core.config import settings
from core.model_router import model_router


SCRIPT_STRATEGY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Jestes doswiadczonym scenarzystem YouTube z 10-letnim doswiadczeniem.
Piszesz scenariusze ktore ludzie chca oglodac DO KONCA.

STRUKTURA 6-CZESCIOWA (Modul II):
1. HOOK (0-30s): Zatrzymaj kciuk. Obietnica lub prowokacja.
2. INTRO (30s-2min): Potwierdz obietnice. Setup napiecia.
3. PROBLEM (2-5min): Zanurz widza w problem. Empatia + dane.
4. DEEPENING (5-10min): Rozwin problem. Historia, przykld, badanie.
5. VALUE (10-18min): Rozwiazanie. Konkretne kroki. Przyklady.
6. CTA (ostatnie 60s): Wezwanie do akcji. Tease nastepnego.

ZASADY JAKOSCI 2026:
- Zero AI stiffness (nie "Oczywiscie!", "W dzisiejszym filmie omowię")
- Jezyk mowiony, nie pisany — czytaj na glos
- Retention reset co 60-90 sekund (micro-payoff, pytanie, zwrot)
- Hook score minimum 8/10 — jezeli slabszy, przepisz
- Sprawdz: czy kazde zdanie jest konieczne?

ODPOWIEDZ JSON:
{{
  "title": "...",
  "main_promise": "Co widz DOSTANIE po obejrzeniu?",
  "knowledge_gap": "Co widz JESZCZE NIE WIE a powinien?",
  "primary_emotion": "curiosity|fear|inspiration|anger|joy",
  "target_viewer": "...",
  "sections": {{
    "hook": {{"text": "...", "duration_seconds": 25, "hook_type": "shock|open_loop|contrarian|curiosity_gap"}},
    "intro": {{"text": "...", "duration_seconds": 90}},
    "problem": {{"text": "...", "duration_seconds": 180}},
    "deepening": {{"text": "...", "duration_seconds": 300}},
    "value": {{"text": "...", "duration_seconds": 480}},
    "cta": {{"text": "...", "duration_seconds": 45}}
  }},
  "retention_resets": [
    {{"at_second": 90, "type": "question|twist|micro_reveal", "text": "..."}}
  ],
  "full_script": "Pelny scenariusz od hooka do CTA",
  "word_count": 0,
  "estimated_duration_minutes": 0.0,
  "hook_score": 0.0,
  "naturalness_score": 0.0,
  "quality_gate_passed": true/false
}}"""),
    ("human", """Temat: {topic}
Kanal: {channel_name}
Obietnica kanalu: {channel_promise}
Pillar: {content_pillar}
Docelowe slowa kluczowe: {keywords}
Docelowy czas: {duration_minutes} minut
Ton: {tone}
Jezyk: {language}"""),
])


class ScriptStrategistAgent(BaseAgent):
    agent_id = "script_strategist"
    layer = 2
    description = "Tworzy pelny 6-czesciowy scenariusz z retention resets i scoring"
    tools = ["Channel Architect output", "topic brief", "audience data", "retention patterns"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("generate_script", self._generate_script)
        workflow.add_node("check_naturalness", self._check_naturalness)
        workflow.add_node("quality_gate", self._quality_gate)

        workflow.add_edge(START, "generate_script")
        workflow.add_edge("generate_script", "check_naturalness")
        workflow.add_edge("check_naturalness", "quality_gate")

        # Conditional: retry if quality gate fails (max 2 iterations)
        workflow.add_conditional_edges(
            "quality_gate",
            self._should_retry,
            {"retry": "generate_script", "done": END},
        )

        return workflow.compile(checkpointer=self._checkpointer)

    async def _generate_script(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        # MACRO tier — complex multi-section script generation
        script_llm = self.get_routed_llm("generate_script", context_length=2000)
        chain = SCRIPT_STRATEGY_PROMPT | script_llm

        response = await chain.ainvoke({
            "topic": input_data.get("topic", ""),
            "channel_name": input_data.get("channel_name", ""),
            "channel_promise": input_data.get("channel_promise", ""),
            "content_pillar": input_data.get("content_pillar", ""),
            "keywords": ", ".join(input_data.get("keywords", [])),
            "duration_minutes": input_data.get("duration_minutes", 12),
            "tone": input_data.get("tone", "authoritative"),
            "language": input_data.get("language", "pl"),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            script = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            script = {"error": "Parse failed", "raw": response.content[:500]}

        state["output_data"]["script"] = script
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        return state

    async def _check_naturalness(self, state: AgentState) -> AgentState:
        """Check if script sounds natural when read aloud."""
        script = state["output_data"].get("script", {})
        full_text = script.get("full_script", "")

        if not full_text or "error" in script:
            state["quality_scores"]["naturalness_score"] = 5.0
            return state

        naturalness_prompt = f"""Oceń naturalność scenariusza YouTube w skali 1-10.
Kryteria: brak AI stiffness, jezyk mowiony nie pisany, rytm zdań.
Zaznacz konkretne problemy.

Scenariusz (pierwsze 500 znakow): {full_text[:500]}

Odpowiedz TYLKO: {{"score": X.X, "issues": ["problem1", "problem2"], "suggestions": ["sug1"]}}"""

        # MICRO tier — simple scoring task
        scorer_llm = self.get_routed_llm("score_hook")
        response = await scorer_llm.ainvoke([("human", naturalness_prompt)])
        try:
            result = json.loads(response.content.strip())
            score = result.get("score", 7.0)
        except (json.JSONDecodeError, ValueError):
            score = 7.0

        state["quality_scores"]["naturalness_score"] = score
        script["naturalness_score"] = score
        return state

    async def _quality_gate(self, state: AgentState) -> AgentState:
        script = state["output_data"].get("script", {})
        hook_score = float(script.get("hook_score", 0))
        naturalness = state["quality_scores"].get("naturalness_score", 0)

        gate_passed = (
            hook_score >= settings.min_hook_score
            and naturalness >= settings.min_naturalness_score
        )

        state["output_data"]["quality_gate"] = {
            "passed": gate_passed,
            "hook_score": hook_score,
            "naturalness_score": naturalness,
            "thresholds": {
                "hook_score": settings.min_hook_score,
                "naturalness_score": settings.min_naturalness_score,
            },
        }
        return state

    def _should_retry(self, state: AgentState) -> str:
        gate = state["output_data"].get("quality_gate", {})
        if not gate.get("passed") and state.get("iteration_count", 0) < 2:
            return "retry"
        return "done"

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        run_id = f"{self.agent_id}-{time.time()}"
        config = {"configurable": {"thread_id": run_id}}
        final_state = await graph.ainvoke(self._initial_state(input_data, run_id=run_id), config)
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


script_strategist_agent = ScriptStrategistAgent()
