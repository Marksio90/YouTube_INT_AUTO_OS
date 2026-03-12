"""
Agent #6: Hook Specialist — Layer 3 (Production)

Generates and scores multiple hook variants for the first 30 seconds.
Quality Gate: Hook Score >= 8/10, Pattern Diversity >= 3 patterns.

Hook patterns: curiosity gap, shock stat, bold claim, story open,
               controversy, before/after, authority, counter-intuitive.

Architecture: Reflection Loop (Generator → Adversarial Critic → Refine)
- Generator (MACRO/gpt-4o): produces 5 hook variants
- Critic (EXPERT/Claude):   adversarially tears them apart — finds weak spots
- Refiner (MACRO/gpt-4o):  addresses critique, produces improved variants
- Scorer (MICRO/gpt-4o-mini): final 0-10 scoring (cheap)
- Gate:                       hook_score >= 8.0 AND diversity >= 3
"""
import json
import time
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

from agents.base import BaseAgent, AgentState
from core.model_router import model_router, TaskComplexity

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

# ── Adversarial Critic Prompt ────────────────────────────────────────────────
HOOK_CRITIC_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a ruthless adversarial critic for YouTube hooks.
Your mission: find EVERY weakness before the hook costs money on TTS/video production.

ATTACK VECTORS to evaluate:
1. Clickbait without delivery — does the hook promise something the video can't fulfil?
2. Vagueness — replace any placeholder-sounding phrase with a concrete example
3. Cliché patterns — "You won't believe...", "Shocking truth..." are dead
4. Emotional mismatch — does the emotion fit the audience's actual pain point?
5. Scroll-stop failure — would THIS hook stop YOUR scroll on mobile at 2am?
6. AI smell — phrases that scream "written by GPT" (e.g. "delve", "game-changer")
7. Pattern diversity — are all hooks structurally identical? Penalise sameness.

For each hook return ONLY the critique JSON — no pleasantries:
{{
  "hooks_critique": [
    {{
      "hook_index": 0,
      "fatal_flaws": ["..."],        // deal-breakers (must fix)
      "minor_weaknesses": ["..."],   // nice-to-fix
      "approved": true/false,        // false = too weak to use
      "suggested_fix": "one-sentence fix direction"
    }}
  ],
  "overall_verdict": "pass|fail|marginal",
  "hooks_approved_count": 2,
  "critique_summary": "..."
}}"""),
    ("human", """Hooks to critique:
{hooks_json}

Video context:
- Title: {title}
- Niche: {niche}
- Target audience: {audience}"""),
])

# ── Refinement Prompt ────────────────────────────────────────────────────────
HOOK_REFINEMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an elite YouTube copywriter. You receive hooks + their critic's feedback.
Rewrite ONLY the rejected/weak hooks to address the fatal flaws.
Keep approved hooks unchanged.

For each hook that needs refinement:
- Address ALL fatal_flaws from the critique
- Keep the same emotional trigger (fear/curiosity/desire/envy)
- Make it more specific: add numbers, timeframes, named entities
- 3-5 sentences maximum for the full hook

RESPOND AS JSON:
{{
  "refined_hooks": [
    {{
      "index": 0,
      "refined": true/false,
      "script": "Full refined hook text",
      "pattern": "curiosity_gap|shock_stat|...",
      "changes_made": ["..."]
    }}
  ]
}}"""),
    ("human", """Original hooks:
{hooks_json}

Critic feedback:
{critique_json}

Niche: {niche} | Audience: {audience}"""),
])


class HookSpecialistAgent(BaseAgent):
    agent_id = "hook_specialist"
    layer = 3
    description = "Generates and scores 4-6 hook variants with Adversarial Critic loop. Gate: score>=8/10"
    tools = ["Hook pattern library", "Emotional trigger scoring", "Open loop detector", "Adversarial Critic"]

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        # Nodes: Generator → Critic → Refiner → Scorer → Gate
        workflow.add_node("generate_hooks", self._generate_hooks)
        workflow.add_node("critique_hooks", self._critique_hooks)
        workflow.add_node("refine_hooks", self._refine_hooks)
        workflow.add_node("score_hooks", self._score_hooks)
        workflow.add_node("select_best", self._select_best)

        workflow.add_edge(START, "generate_hooks")
        workflow.add_edge("generate_hooks", "critique_hooks")

        # After critique: if verdict is "pass" skip refinement, else refine
        workflow.add_conditional_edges(
            "critique_hooks",
            self._should_refine,
            {"refine": "refine_hooks", "skip": "score_hooks"},
        )
        workflow.add_edge("refine_hooks", "score_hooks")
        workflow.add_edge("score_hooks", "select_best")
        workflow.add_edge("select_best", END)

        return workflow.compile()

    def _should_refine(self, state: AgentState) -> str:
        """Route after critique: refine if any hook was rejected."""
        critique = state["output_data"].get("critique", {})
        verdict = critique.get("overall_verdict", "fail")
        approved_count = critique.get("hooks_approved_count", 0)
        total_hooks = len(state["output_data"].get("hooks_raw", {}).get("hooks", []))
        # Refine if any hooks rejected OR fewer than 3 approved
        if verdict == "pass" and approved_count >= 3:
            return "skip"
        return "refine"

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

    async def _critique_hooks(self, state: AgentState) -> AgentState:
        """Adversarial Critic (EXPERT tier — Claude) tears hooks apart before spending on TTS."""
        hooks_data = state["output_data"].get("hooks_raw", {})
        hooks = hooks_data.get("hooks", [])
        input_data = state["input_data"]

        # Use EXPERT model for critic role (adversarial reasoning)
        critic_llm = model_router.get_llm(
            task_type="critique_hooks",
            context_length=len(str(hooks)) // 4,
            callbacks=self._langfuse_callbacks,
        )
        chain = HOOK_CRITIC_PROMPT | critic_llm

        try:
            resp = await chain.ainvoke({
                "hooks_json": json.dumps(
                    [{"index": i, "script": h.get("script", ""), "pattern": h.get("pattern", "")}
                     for i, h in enumerate(hooks)],
                    ensure_ascii=False,
                ),
                "title": input_data.get("title", ""),
                "niche": input_data.get("niche", ""),
                "audience": input_data.get("target_audience", ""),
            })
            content = resp.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            critique = json.loads(content.strip())
        except Exception as e:
            self.logger.warning("Hook critique failed, using empty critique", error=str(e))
            critique = {
                "hooks_critique": [],
                "overall_verdict": "marginal",
                "hooks_approved_count": len(hooks),
                "critique_summary": "Critique unavailable — proceeding",
            }

        state["output_data"]["critique"] = critique
        self.logger.info(
            "Hook critique complete",
            verdict=critique.get("overall_verdict"),
            approved=critique.get("hooks_approved_count"),
        )
        return state

    async def _refine_hooks(self, state: AgentState) -> AgentState:
        """Refiner (MACRO tier — gpt-4o) rewrites rejected hooks based on critic feedback."""
        hooks_data = state["output_data"].get("hooks_raw", {})
        hooks = hooks_data.get("hooks", [])
        critique = state["output_data"].get("critique", {})
        input_data = state["input_data"]

        # MACRO model for creative refinement
        refiner_llm = model_router.get_llm(
            task_type="generate_hook_variants",
            context_length=len(str(hooks) + str(critique)) // 4,
            callbacks=self._langfuse_callbacks,
        )
        chain = HOOK_REFINEMENT_PROMPT | refiner_llm

        try:
            resp = await chain.ainvoke({
                "hooks_json": json.dumps(
                    [{"index": i, "script": h.get("script", ""), "pattern": h.get("pattern", "")}
                     for i, h in enumerate(hooks)],
                    ensure_ascii=False,
                ),
                "critique_json": json.dumps(critique, ensure_ascii=False),
                "niche": input_data.get("niche", ""),
                "audience": input_data.get("target_audience", ""),
            })
            content = resp.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            refinement = json.loads(content.strip())

            # Merge refined hooks back into hooks list
            for refined in refinement.get("refined_hooks", []):
                idx = refined.get("index")
                if idx is not None and 0 <= idx < len(hooks) and refined.get("refined"):
                    hooks[idx]["script"] = refined.get("script", hooks[idx]["script"])
                    hooks[idx]["refinement_applied"] = True
                    hooks[idx]["changes_made"] = refined.get("changes_made", [])

            hooks_data["hooks"] = hooks
            state["output_data"]["hooks_raw"] = hooks_data
            state["output_data"]["refinement"] = refinement

        except Exception as e:
            self.logger.warning("Hook refinement failed, using originals", error=str(e))

        return state

    async def _score_hooks(self, state: AgentState) -> AgentState:
        hooks_data = state["output_data"].get("hooks_raw", {})
        hooks = hooks_data.get("hooks", [])
        input_data = state["input_data"]
        context = f"Niche: {input_data.get('niche', '')} | Audience: {input_data.get('target_audience', '')}"

        # MICRO model for scoring — cheap, fast, no creativity needed
        scorer_llm = model_router.get_llm(
            task_type="score_hook",
            callbacks=self._langfuse_callbacks,
        )

        scored_hooks = []
        for hook in hooks:
            chain = HOOK_SCORING_PROMPT | scorer_llm
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
