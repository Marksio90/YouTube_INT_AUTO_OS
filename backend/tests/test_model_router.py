"""Tests for the Model Router — cost-optimized LLM selection."""
import pytest
from core.model_router import ModelRouter, TaskComplexity, TASK_REGISTRY


class TestModelRouter:
    def setup_method(self):
        self.router = ModelRouter()

    def test_nano_task_routes_to_fast_model(self):
        decision = self.router.route("classify_niche")
        assert decision.complexity == TaskComplexity.NANO
        assert decision.estimated_cost_tier == "very_low"
        assert decision.provider == "openai"

    def test_micro_task_routes_to_fast_model(self):
        decision = self.router.route("score_hook")
        assert decision.complexity == TaskComplexity.MICRO
        assert decision.estimated_cost_tier == "low"

    def test_macro_task_routes_to_premium_model(self):
        decision = self.router.route("generate_script")
        assert decision.complexity == TaskComplexity.MACRO
        assert decision.estimated_cost_tier == "medium"

    def test_expert_task_routes_to_high_tier(self):
        decision = self.router.route("critique_hooks")
        assert decision.complexity == TaskComplexity.EXPERT
        assert decision.estimated_cost_tier == "high"

    def test_unknown_task_defaults_to_macro(self):
        decision = self.router.route("some_unknown_task")
        assert decision.complexity == TaskComplexity.MACRO

    def test_context_length_upgrades_tier(self):
        decision = self.router.route("score_hook", context_length=10000)
        # MICRO should upgrade to MACRO due to long context
        assert decision.complexity == TaskComplexity.MACRO

    def test_force_complexity_overrides_registry(self):
        decision = self.router.route(
            "classify_niche",
            force_complexity=TaskComplexity.EXPERT,
        )
        assert decision.complexity == TaskComplexity.EXPERT

    def test_routing_stats_tracks_decisions(self):
        self.router.route("classify_niche")
        self.router.route("generate_script")
        self.router.route("critique_hooks")
        stats = self.router.get_routing_stats()
        assert stats["total_decisions"] == 3
        assert "by_cost_tier" in stats
        assert "estimated_savings_pct" in stats

    def test_all_registered_tasks_have_valid_complexity(self):
        for task_type, (complexity, desc) in TASK_REGISTRY.items():
            assert isinstance(complexity, TaskComplexity), f"{task_type} has invalid complexity"
            assert len(desc) > 0, f"{task_type} has empty description"

    def test_savings_estimate_is_positive_for_mixed_workload(self):
        # Simulate realistic workload
        for _ in range(10):
            self.router.route("classify_niche")  # NANO
        for _ in range(5):
            self.router.route("score_hook")  # MICRO
        self.router.route("generate_script")  # MACRO
        self.router.route("critique_hooks")  # EXPERT

        stats = self.router.get_routing_stats()
        assert stats["estimated_savings_pct"] > 0
