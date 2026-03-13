"""
Base agent infrastructure for YouTube Intelligence & Automation OS.
All 23 agents inherit from BaseAgent and use LangGraph for orchestration.
"""
from typing import Any, Dict, Optional, TypedDict, Annotated
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import structlog
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
import operator

from core.config import settings
from core.langfuse import get_langfuse_callbacks
from core.model_router import model_router, TaskComplexity

logger = structlog.get_logger(__name__)


# ============================================================
# Agent State
# ============================================================

class AgentState(TypedDict):
    """Shared state for all agents in a workflow."""
    messages: Annotated[list[BaseMessage], operator.add]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    quality_scores: Dict[str, float]
    errors: list[str]
    agent_id: str
    run_id: str
    video_project_id: Optional[str]
    channel_id: Optional[str]
    iteration_count: int
    max_iterations: int


# ============================================================
# Base Agent
# ============================================================

class BaseAgent(ABC):
    """
    Base class for all 23 YouTube Automation OS agents.
    Each agent is a LangGraph state machine with quality gates.

    Features:
    - MemorySaver checkpointing for fault-tolerant execution
    - model_router integration for cost-optimized LLM selection
    - Langfuse observability callbacks
    """

    agent_id: str = "base_agent"
    layer: int = 1
    description: str = "Base agent"
    tools: list = []

    def __init__(self):
        langfuse_callbacks = get_langfuse_callbacks(
            trace_name=self.agent_id,
            tags=[f"layer_{self.layer}", "agent"],
        )
        self._langfuse_callbacks = langfuse_callbacks
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._graph = None
        self._checkpointer = MemorySaver()

        # Convenience LLM instances — backed by model_router for cost optimization
        self.llm_premium = model_router.get_llm(
            "generate_script", callbacks=langfuse_callbacks
        )
        self.llm_fast = model_router.get_llm(
            "score_hook", callbacks=langfuse_callbacks
        )

    def get_routed_llm(self, task_type: str, context_length: int = 0):
        """Get LLM via model_router for cost-optimized model selection.

        Prefer this over self.llm_premium / self.llm_fast for automatic
        NANO/MICRO/MACRO/EXPERT tier routing.
        """
        return model_router.get_llm(
            task_type=task_type,
            context_length=context_length,
            callbacks=self._langfuse_callbacks,
        )

    def get_graph(self) -> StateGraph:
        if not self._graph:
            self._graph = self._build_graph()
        return self._graph

    @abstractmethod
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine for this agent."""
        pass

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent and return results."""
        pass

    async def check_quality_gates(self, output: Dict[str, Any]) -> Dict[str, float]:
        """Check quality gate scores. Override per agent."""
        return {}

    def _initial_state(self, input_data: Dict[str, Any], run_id: str = "") -> AgentState:
        return AgentState(
            messages=[],
            input_data=input_data,
            output_data={},
            quality_scores={},
            errors=[],
            agent_id=self.agent_id,
            run_id=run_id or f"{self.agent_id}-{datetime.now(timezone.utc).timestamp()}",
            video_project_id=input_data.get("video_project_id"),
            channel_id=input_data.get("channel_id"),
            iteration_count=0,
            max_iterations=3,
        )

    def _log_start(self, input_data: Dict[str, Any]) -> None:
        self.logger.info(
            "Agent starting",
            agent_id=self.agent_id,
            layer=self.layer,
            input_keys=list(input_data.keys()),
        )

    def _log_complete(self, output_data: Dict[str, Any], duration_s: float) -> None:
        self.logger.info(
            "Agent completed",
            agent_id=self.agent_id,
            duration_seconds=round(duration_s, 2),
            output_keys=list(output_data.keys()),
        )
