"""
Dynamic Model Router — Mixture of Experts for LLM selection.

Routes each task to the cheapest/fastest model capable of handling it.
Saves ~60-70% on LLM costs by avoiding GPT-4o for simple tasks.

Task complexity tiers:
  NANO   → local/cheap: tagging, classification, yes/no decisions
  MICRO  → fast model (gpt-4o-mini / haiku): summarization, scoring, short generation
  MACRO  → premium model (gpt-4o / claude-sonnet): strategy, complex writing, reasoning
  EXPERT → heavyweight (claude-opus / o1): legal analysis, adversarial critique, deep research

Usage:
    from core.model_router import model_router, TaskComplexity

    llm = model_router.get_llm(
        task_type="score_hook",
        context_length=300,
        requires_json=True,
    )
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class TaskComplexity(str, enum.Enum):
    NANO = "nano"       # Pure classification / yes-no / label picking
    MICRO = "micro"     # Scoring, short text, simple rewrites
    MACRO = "macro"     # Multi-step reasoning, strategy, long-form generation
    EXPERT = "expert"   # Adversarial critique, legal, originality deep-check


# ------------------------------------------------------------------ #
# Task Registry
# Maps task_type → (complexity, description)
# ------------------------------------------------------------------ #

TASK_REGISTRY: dict[str, tuple[TaskComplexity, str]] = {
    # Nano tasks ─────────────────────────────────────────────────
    "classify_niche":           (TaskComplexity.NANO,   "Binary niche classification"),
    "tag_video":                (TaskComplexity.NANO,   "Assign genre/format tags"),
    "detect_language":          (TaskComplexity.NANO,   "Language detection"),
    "flag_risk":                (TaskComplexity.NANO,   "Red/yellow/green risk flag"),
    "route_pipeline_stage":     (TaskComplexity.NANO,   "Decide next pipeline step"),

    # Micro tasks ─────────────────────────────────────────────────
    "score_hook":               (TaskComplexity.MICRO,  "Numeric hook scoring 0-10"),
    "score_retention":          (TaskComplexity.MICRO,  "Predict retention % per segment"),
    "score_seo":                (TaskComplexity.MICRO,  "SEO keyword density scoring"),
    "score_originality":        (TaskComplexity.MICRO,  "Cosine similarity scoring"),
    "summarize_competitor":     (TaskComplexity.MICRO,  "Summarize competitor video"),
    "extract_keywords":         (TaskComplexity.MICRO,  "Pull top-N keywords from text"),
    "generate_tags":            (TaskComplexity.MICRO,  "Generate YouTube tag list"),
    "rewrite_cta":              (TaskComplexity.MICRO,  "Short CTA rewrite"),
    "check_ypp_policy":         (TaskComplexity.MICRO,  "YPP policy compliance check"),

    # Macro tasks ─────────────────────────────────────────────────
    "generate_script":          (TaskComplexity.MACRO,  "Full 6-part script generation"),
    "generate_hook_variants":   (TaskComplexity.MACRO,  "4-6 hook variants"),
    "generate_title_variants":  (TaskComplexity.MACRO,  "SEO title A/B variants"),
    "retention_engineering":    (TaskComplexity.MACRO,  "Inject retention devices into script"),
    "niche_analysis":           (TaskComplexity.MACRO,  "7-factor niche scoring with gap analysis"),
    "storyboard_generation":    (TaskComplexity.MACRO,  "Scene-by-scene storyboard"),
    "seo_optimization":         (TaskComplexity.MACRO,  "Full SEO metadata package"),
    "channel_strategy":         (TaskComplexity.MACRO,  "Long-term channel positioning"),
    "localize_format":          (TaskComplexity.MACRO,  "Platform-specific format adaptation"),

    # Expert tasks ────────────────────────────────────────────────
    "critique_hooks":           (TaskComplexity.EXPERT, "Adversarial critique of generated hooks"),
    "critique_script":          (TaskComplexity.EXPERT, "Deep script adversarial review"),
    "deep_originality_check":   (TaskComplexity.EXPERT, "Legal-grade originality & copyright analysis"),
    "competitive_deconstruction":(TaskComplexity.EXPERT,"Deep competitor channel anatomy"),
    "opportunity_mapping":      (TaskComplexity.EXPERT, "Blue-ocean opportunity research"),
}


@dataclass
class RoutingDecision:
    task_type: str
    complexity: TaskComplexity
    model_id: str
    provider: str           # "openai" | "anthropic"
    temperature: float
    reason: str
    estimated_cost_tier: str   # "very_low" | "low" | "medium" | "high"


@dataclass
class ModelRouterConfig:
    # Override model IDs from env/config
    nano_model: str = field(default_factory=lambda: settings.openai_model_fast)
    micro_model: str = field(default_factory=lambda: settings.openai_model_fast)
    macro_model: str = field(default_factory=lambda: settings.openai_model_premium)
    expert_model: str = field(default_factory=lambda: settings.anthropic_model)

    # Context length thresholds that force upgrade
    context_upgrade_threshold: int = 8000   # tokens


class ModelRouter:
    """
    Routes agent tasks to the optimal LLM based on task complexity,
    context length, and cost constraints.

    Design principles:
    - NANO / MICRO tasks NEVER use premium models (saves ~80% cost)
    - EXPERT tasks prefer Claude for stronger reasoning / critique
    - Context length > threshold forces one tier upgrade
    - All decisions are logged for cost analytics
    """

    def __init__(self, config: Optional[ModelRouterConfig] = None):
        self.config = config or ModelRouterConfig()
        self._decision_log: list[RoutingDecision] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def route(
        self,
        task_type: str,
        context_length: int = 0,
        requires_json: bool = False,
        force_complexity: Optional[TaskComplexity] = None,
    ) -> RoutingDecision:
        """
        Determine the best model for a task.

        Args:
            task_type:        Key from TASK_REGISTRY (or freeform — defaults to MACRO)
            context_length:   Approximate token count of input context
            requires_json:    Whether the model must output valid JSON
            force_complexity: Override the registry lookup

        Returns:
            RoutingDecision with model_id, provider, temperature, cost tier
        """
        base_complexity, task_desc = TASK_REGISTRY.get(
            task_type, (TaskComplexity.MACRO, task_type)
        )
        complexity = force_complexity or base_complexity

        # Upgrade tier if context is very long
        if context_length > self.config.context_upgrade_threshold:
            complexity = self._upgrade_complexity(complexity)
            reason_suffix = f" (upgraded: context={context_length} tokens)"
        else:
            reason_suffix = ""

        model_id, provider, temperature, cost_tier = self._select_model(complexity, requires_json)

        decision = RoutingDecision(
            task_type=task_type,
            complexity=complexity,
            model_id=model_id,
            provider=provider,
            temperature=temperature,
            reason=f"{task_desc}{reason_suffix}",
            estimated_cost_tier=cost_tier,
        )
        self._decision_log.append(decision)
        logger.debug(
            "Model routed",
            task=task_type,
            complexity=complexity.value,
            model=model_id,
            cost_tier=cost_tier,
        )
        return decision

    def get_llm(
        self,
        task_type: str,
        context_length: int = 0,
        requires_json: bool = False,
        force_complexity: Optional[TaskComplexity] = None,
        callbacks: list = None,
    ):
        """
        Convenience method: route + instantiate the LLM in one call.

        Returns a LangChain-compatible ChatModel instance.
        """
        decision = self.route(task_type, context_length, requires_json, force_complexity)
        return self._build_llm(decision, callbacks or [])

    def get_routing_stats(self) -> dict:
        """Return aggregated routing statistics for cost analytics."""
        if not self._decision_log:
            return {"total": 0}

        by_tier: dict[str, int] = {}
        for d in self._decision_log:
            by_tier[d.estimated_cost_tier] = by_tier.get(d.estimated_cost_tier, 0) + 1

        return {
            "total_decisions": len(self._decision_log),
            "by_cost_tier": by_tier,
            "estimated_savings_pct": self._estimate_savings(),
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _select_model(
        self, complexity: TaskComplexity, requires_json: bool
    ) -> tuple[str, str, float, str]:
        """Return (model_id, provider, temperature, cost_tier)."""
        if complexity == TaskComplexity.NANO:
            return self.config.nano_model, "openai", 0.0, "very_low"

        if complexity == TaskComplexity.MICRO:
            return self.config.micro_model, "openai", 0.3, "low"

        if complexity == TaskComplexity.MACRO:
            return self.config.macro_model, "openai", 0.7, "medium"

        # EXPERT → prefer Claude for adversarial critique & deep reasoning
        if settings.anthropic_api_key:
            return self.config.expert_model, "anthropic", 0.7, "high"
        # Fallback to GPT-4o if no Anthropic key
        return self.config.macro_model, "openai", 0.7, "high"

    def _upgrade_complexity(self, complexity: TaskComplexity) -> TaskComplexity:
        """Move one tier up due to long context."""
        order = [TaskComplexity.NANO, TaskComplexity.MICRO, TaskComplexity.MACRO, TaskComplexity.EXPERT]
        idx = order.index(complexity)
        return order[min(idx + 1, len(order) - 1)]

    def _build_llm(self, decision: RoutingDecision, callbacks: list):
        """Instantiate the appropriate LangChain ChatModel."""
        if decision.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=decision.model_id,
                api_key=settings.anthropic_api_key,
                temperature=decision.temperature,
                max_retries=3,
            )

        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=decision.model_id,
            api_key=settings.openai_api_key,
            openai_organization=settings.openai_org_id or None,
            temperature=decision.temperature,
            max_retries=3,
            callbacks=callbacks,
        )

    def _estimate_savings(self) -> float:
        """
        Rough estimate of cost saved vs routing everything to MACRO.
        NANO ≈ 2% of MACRO cost, MICRO ≈ 5%, MACRO = 100%, EXPERT ≈ 150%.
        """
        tier_weights = {"very_low": 0.02, "low": 0.05, "medium": 1.0, "high": 1.5}
        total_actual = sum(
            tier_weights.get(d.estimated_cost_tier, 1.0)
            for d in self._decision_log
        )
        total_if_all_macro = len(self._decision_log) * 1.0
        if total_if_all_macro == 0:
            return 0.0
        saved = 1.0 - (total_actual / total_if_all_macro)
        return round(saved * 100, 1)


# Singleton — import and use directly
model_router = ModelRouter()
