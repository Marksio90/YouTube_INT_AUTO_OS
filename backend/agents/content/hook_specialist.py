"""
Agent #6: Hook Specialist — Layer 3 (Production)

Generates and scores multiple hook variants for the first 30 seconds.
Quality Gate: Hook Score >= 8/10, Pattern Diversity >= 3 patterns.

Hook patterns: curiosity gap, shock stat, bold claim, story open,
               controversy, before/after, authority, counter-intuitive.
"""
import json
import time
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState

HOOK_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an elite YouTube hook specialist. You craft the first 30 seconds that make viewers stay.

HOOK SCIENCE:
- First 3 seconds: Pattern interrupt — stop the scroll
- Seconds 3-15: Raise the stakes — why this matters NOW
- Seconds 15-30: Open a loop — they MUST watch to close it

HOOK PATTERNS (generate at least 4 variants):
1. Curiosity Gap: "Most people don't know that..."
2. Shock Stat: "X% of [audience] will [shocking outcome]"
3. Bold Claim: "I [achieved X] in [time] without [common method]"
4. Story Open: "Three years ago I [relatable failure]..."
5. Controversy: "Everyone is wrong about [topic]"
6. Before/After: "In 90 days [transformation] — here's exactly how"
7. Authority: "After [credibility] I discovered..."
8. Counter-Intuitive: "Stop [conventional advice] — it's actually [opposite]"

SCORING (0-10):
- Specificity: Concrete numbers/timeframes beat vague claims
- Emotional resonance: Fear, curiosity, desire, envy
- Pattern interrupt: Does it break expected patterns?
- Promise clarity: Is the value proposition crystal clear?
- Authenticity: Feels human, not AI-generated

RESPOND AS JSON:
{{
  "hooks": [
    {{
      "pattern": "curiosity_gap",
      "script": "Full 30-second hook text (3-5 sentences)",
      "hook_score": 8.5,
      "open_loop": "what question does this leave open?",
      "emotional_trigger": "fear|curiosity|desire|envy|inspiration",
      "first_3_seconds": "exact opening line",
      "cta_to_continue": "why they must keep watching"
    }}
  ],
  "best_hook_index": 0,
  "pattern_diversity_score": 4,
  "overall_notes": "..."
}}"""),
    ("human", """Title: {title}
Script excerpt (first 500 chars): {script_excerpt}
Target audience: {audience}
Niche: {niche}
Emotional tone: {tone}
Generate {n_variants} hook variants."""),
])

HOOK_SCORING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Score this YouTube hook on a 0-10 scale across 5 dimensions.
Be strict — 8+ requires genuine excellence.

RESPOND AS JSON:
{{
  "specificity": 0-10,
  "emotional_resonance": 0-10,
  "pattern_interrupt": 0-10,
  "promise_clarity": 0-10,
  "authenticity": 0-10,
  "overall_score": 0-10,
  "strengths": ["..."],
  "improvements": ["..."]
}}"""),
    ("human", "Hook to score:\n{hook_text}\n\nContext: {context}"),
])


class HookSpecialistAgent(BaseAgent):
    agent_id = "hook_specialist"
    layer = 3
    description = "Generates and scores 4-6 hook variants with Quality Gate >= 8/10"
    tools = ["Hook pattern library", "Emotional trigger scoring", "Open loop detector"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("generate_hooks", self._generate_hooks)
        workflow.add_node("score_hooks", self._score_hooks)
        workflow.add_node("select_best", self._select_best)

        workflow.add_edge(START, "generate_hooks")
        workflow.add_edge("generate_hooks", "score_hooks")
        workflow.add_edge("score_hooks", "select_best")
        workflow.add_edge("select_best", END)

        return workflow.compile()

    async def _generate_hooks(self, state: AgentState) -> AgentState:
        input_data = state["input_data"]
        chain = HOOK_GENERATION_PROMPT | self.llm_premium

        response = await chain.ainvoke({
            "title": input_data.get("title", ""),
            "script_excerpt": input_data.get("script_text", "")[:500],
            "audience": input_data.get("target_audience", "general YouTube viewers"),
            "niche": input_data.get("niche", ""),
            "tone": input_data.get("tone", "engaging and authoritative"),
            "n_variants": input_data.get("n_hooks", 5),
        })

        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            hooks_data = json.loads(content.strip())
        except (json.JSONDecodeError, IndexError):
            hooks_data = {
                "hooks": [],
                "best_hook_index": 0,
                "pattern_diversity_score": 0,
                "error": "Parse failed",
            }

        state["output_data"]["hooks_raw"] = hooks_data
        return state

    async def _score_hooks(self, state: AgentState) -> AgentState:
        hooks_data = state["output_data"].get("hooks_raw", {})
        hooks = hooks_data.get("hooks", [])
        input_data = state["input_data"]
        context = f"Niche: {input_data.get('niche', '')} | Audience: {input_data.get('target_audience', '')}"

        scored_hooks = []
        for hook in hooks:
            chain = HOOK_SCORING_PROMPT | self.llm_fast
            try:
                resp = await chain.ainvoke({
                    "hook_text": hook.get("script", ""),
                    "context": context,
                })
                content = resp.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                scores = json.loads(content.strip())
                hook["detailed_scores"] = scores
                hook["hook_score"] = scores.get("overall_score", hook.get("hook_score", 7))
            except Exception:
                pass
            scored_hooks.append(hook)

        state["output_data"]["hooks_scored"] = scored_hooks
        return state

    async def _select_best(self, state: AgentState) -> AgentState:
        hooks = state["output_data"].get("hooks_scored", [])
        hooks_raw = state["output_data"].get("hooks_raw", {})

        if not hooks:
            state["output_data"]["final"] = {
                "best_hook": None,
                "all_hooks": [],
                "quality_gate_passed": False,
                "max_hook_score": 0,
            }
            return state

        best = max(hooks, key=lambda h: h.get("hook_score", 0))
        max_score = best.get("hook_score", 0)
        diversity = hooks_raw.get("pattern_diversity_score", len({h.get("pattern") for h in hooks}))

        gate_passed = max_score >= 8.0 and diversity >= 3

        state["output_data"]["final"] = {
            "best_hook": best,
            "all_hooks": hooks,
            "max_hook_score": max_score,
            "pattern_diversity": diversity,
            "quality_gate_passed": gate_passed,
            "quality_gate_threshold": 8.0,
            "message": (
                f"Hook gate PASSED: {max_score:.1f}/10, {len(hooks)} variants, {diversity} patterns"
                if gate_passed
                else f"Hook gate FAILED: Best score {max_score:.1f}/10 < 8.0 or diversity {diversity} < 3"
            ),
        }
        state["quality_scores"]["hook_score"] = max_score
        state["quality_scores"]["hook_diversity"] = float(diversity)
        return state

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self._log_start(input_data)
        start = time.time()
        graph = self.get_graph()
        final_state = await graph.ainvoke(self._initial_state(input_data))
        duration = time.time() - start
        self._log_complete(final_state["output_data"], duration)
        return {**final_state["output_data"], "agent_id": self.agent_id, "duration_seconds": round(duration, 2)}


hook_specialist_agent = HookSpecialistAgent()
