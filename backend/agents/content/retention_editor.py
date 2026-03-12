"""
Agent #7: Retention Editor — Layer 3 (Production)

Analyzes script for predicted retention drops and injects retention
devices at critical points.

Quality Gate: Predicted avg retention >= 55%, no >15% single drop.
Retention devices: callbacks, pattern interrupts, mini-cliffhangers,
                   curiosity loops, progress markers, value spikes.

Architecture: Reflection Loop with max 2 cycles
- Analyze retention curve → inject devices → re-evaluate → gate
- If gate fails on cycle 1, re-inject (up to max_iterations)
- Uses MACRO model for injection, MICRO for re-scoring
"""
import json
import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState
from core.model_router import model_router


RETENTION_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube retention engineering expert. You analyze scripts and predict where viewers drop off.

RETENTION DROP TRIGGERS:
- Slow intros after hook (>45s without value delivery)
- Information overload (>3 concepts without breathing room)
- Monotone delivery sections (no variation in pacing)
- Missing transitions between topics
- Long tangents without payoff
- Weak mid-point — the 50% dropout cliff
- No closing loop from opening hook

RETENTION DEVICES TO INJECT:
1. Callback: Reference earlier content ("remember when I said X?")
2. Pattern interrupt: Sudden format change, rhetorical question
3. Mini-cliffhanger: "Before I show you the answer, you need to understand X"
4. Progress marker: "We're halfway there — here's what we've covered"
5. Value spike: Quick, unexpected insight or tip
6. Curiosity loop: Open new question before answering current one
7. Social proof drop: "This is what [X] people discovered"

SEGMENT ANALYSIS:
Divide script into 10% segments. For each: predict retention% and flag drops.

RESPOND AS JSON:
{{
  "segments": [
    {{
      "position_pct": 0,
      "content_summary": "...",
      "predicted_retention": 100,
      "drop_risk": "none|low|medium|high",
      "drop_reason": "...",
      "retention_device_injected": null
    }}
  ],
  "predicted_avg_retention": 58.5,
  "predicted_max_drop_pct": 12.3,
  "critical_drop_points": [45, 180],
  "devices_injected": 4,
  "revised_script_sections": {{"section_timestamp": "revised text"}},
  "quality_gate_passed": true,
  "retention_score": 72,
  "recommendations": ["..."]
}}"""),
    ("human", """Script: {script_text}

Title: {title}
Duration estimate (seconds): {duration_est}
Video format: {format}"""),
])


RETENTION_RESCORE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a YouTube retention analyst. Re-evaluate a script AFTER retention devices were injected.
Score quickly — focus on whether the injected devices actually help.

RESPOND AS JSON:
{{
  "predicted_avg_retention": 0-100,
  "predicted_max_drop_pct": 0-100,
  "improvement_vs_previous": "+X.X%",
  "devices_effective": true/false,
  "remaining_weak_spots": ["timestamp: reason"],
  "quality_gate_passed": true/false
}}"""),
    ("human", """Revised script (with injected devices):
{revised_script}

Previous scores:
- Avg retention: {prev_avg}%
- Max drop: {prev_max_drop}%
- Devices injected: {devices_count}"""),
])


class RetentionEditorAgent(BaseAgent):
    agent_id = "retention_editor"
    layer = 3
    description = "Predicts retention curve, reflection loop up to 2x. Gate: avg>=55%, max drop<15%"
    tools = ["Retention drop predictor", "Script surgery tool", "Pacing analyzer", "Reflection scorer"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze_retention", self._analyze_retention)
        workflow.add_node("inject_devices", self._inject_devices)
        workflow.add_node("rescore_retention", self._rescore_retention)
        workflow.add_node("finalize", self._finalize)

        workflow.add_edge(START, "analyze_retention")
        workflow.add_edge("analyze_retention", "inject_devices")
        workflow.add_edge("inject_devices", "rescore_retention")

        # Reflection: if gate still fails and iterations remain, inject again
        workflow.add_conditional_edges(
            "rescore_retention",
            self._should_re_inject,
            {"retry": "inject_devices", "done": "finalize"},
        )
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _should_re_inject(self, state: AgentState) -> str:
        """Continue reflection loop if gate failed and iterations remain."""
        rescore = state["output_data"].get("rescore", {})
        gate_passed = rescore.get("quality_gate_passed", False)
        iteration = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", 2)
        if gate_passed or iteration >= max_iter:
            return "done"
        return "retry"

    async def _analyze_retention(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        # MACRO model: multi-segment analysis requires reasoning depth
        analysis_llm = model_router.get_llm(
            task_type="retention_engineering",
            context_length=len(input_data.get("script_text", "")) // 4,
            callbacks=self._langfuse_callbacks,
        )
        chain = RETENTION_ANALYSIS_PROMPT | analysis_llm

        script_text = input_data.get("script_text", "")
        # Estimate duration from word count (avg 130 words/min)
        word_count = len(script_text.split())
        duration_est = int(word_count / 130 * 60)

        response = await chain.ainvoke({
            "script_text": script_text[:4000],
            "title": input_data.get("title", ""),
            "duration_est": duration_est,
            "format": input_data.get("format", "educational"),
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
                "predicted_avg_retention": 50.0,
                "predicted_max_drop_pct": 20.0,
                "devices_injected": 0,
                "quality_gate_passed": False,
                "error": "Parse failed",
            }

        state["output_data"]["retention_analysis"] = analysis
        return state

    async def _inject_devices(self, state: AgentState) -> AgentState:
        """If critical drops exist, generate specific injection text."""
        analysis = state["output_data"].get("retention_analysis", {})
        critical_points = analysis.get("critical_drop_points", [])

        if not critical_points or analysis.get("quality_gate_passed", False):
            state["output_data"]["injections"] = []
            return state

        # Already handled in the analysis prompt — just extract
        state["output_data"]["injections"] = analysis.get("revised_script_sections", {})
        return state

    async def _rescore_retention(self, state: AgentState) -> AgentState:
        """Re-evaluate retention after device injection — MICRO model (cheap)."""
        analysis = state["output_data"].get("retention_analysis", {})
        injections = state["output_data"].get("injections", {})

        # Build revised script text by merging original + injected sections
        original_text = state["input_data"].get("script_text", "")
        revised_sections = injections if isinstance(injections, dict) else {}
        revised_text = original_text
        for _ts, new_text in revised_sections.items():
            revised_text += f"\n\n[INJECTED DEVICE]: {new_text}"

        rescore_llm = model_router.get_llm(
            task_type="score_retention",
            callbacks=self._langfuse_callbacks,
        )
        chain = RETENTION_RESCORE_PROMPT | rescore_llm

        try:
            resp = await chain.ainvoke({
                "revised_script": revised_text[:3000],
                "prev_avg": analysis.get("predicted_avg_retention", 50.0),
                "prev_max_drop": analysis.get("predicted_max_drop_pct", 25.0),
                "devices_count": analysis.get("devices_injected", 0),
            })
            content = resp.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            rescore = json.loads(content.strip())
        except Exception as e:
            self.logger.warning("Retention re-score failed", error=str(e))
            rescore = {
                "predicted_avg_retention": analysis.get("predicted_avg_retention", 50.0),
                "predicted_max_drop_pct": analysis.get("predicted_max_drop_pct", 25.0),
                "quality_gate_passed": False,
            }

        state["output_data"]["rescore"] = rescore
        # Increment iteration counter for loop guard
        state["iteration_count"] = state.get("iteration_count", 0) + 1

        self.logger.info(
            "Retention re-scored",
            iteration=state["iteration_count"],
            avg=rescore.get("predicted_avg_retention"),
            gate=rescore.get("quality_gate_passed"),
        )
        return state

    async def _finalize(self, state: AgentState) -> AgentState:
        # Prefer rescore data if available (post-reflection), else use initial analysis
        rescore = state["output_data"].get("rescore", {})
        analysis = state["output_data"].get("retention_analysis", {})

        avg_retention = rescore.get("predicted_avg_retention") or analysis.get("predicted_avg_retention", 50.0)
        max_drop = rescore.get("predicted_max_drop_pct") or analysis.get("predicted_max_drop_pct", 25.0)

        gate_passed = avg_retention >= 55.0 and max_drop <= 15.0

        state["output_data"]["final"] = {
            "predicted_avg_retention": avg_retention,
            "predicted_max_drop_pct": max_drop,
            "devices_injected": analysis.get("devices_injected", 0),
            "segments": analysis.get("segments", []),
            "recommendations": analysis.get("recommendations", []),
            "quality_gate_passed": gate_passed,
            "retention_score": analysis.get("retention_score", int(avg_retention)),
            "reflection_cycles": state.get("iteration_count", 0),
            "rescore_data": state["output_data"].get("rescore", {}),
            "message": (
                f"Retention gate PASSED: {avg_retention:.1f}% avg, {max_drop:.1f}% max drop "
                f"(after {state.get('iteration_count', 0)} reflection cycle(s))"
                if gate_passed
                else f"Retention gate FAILED: avg {avg_retention:.1f}% < 55% or max drop {max_drop:.1f}% > 15%"
            ),
        }
        state["quality_scores"]["retention_score"] = avg_retention
        state["quality_scores"]["max_drop"] = max_drop
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


retention_editor_agent = RetentionEditorAgent()
