"""
Base agent infrastructure for YouTube Intelligence & Automation OS.
All 23 agents inherit from BaseAgent and use LangGraph for orchestration.
"""
from typing import Any, Dict, Optional, TypedDict, Annotated
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import structlog
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
import operator

from core.config import settings

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
# LLM Factory
# ============================================================

def get_premium_llm() -> ChatOpenAI:
    """GPT-4o for complex analysis and generation."""
    return ChatOpenAI(
        model=settings.openai_model_premium,
        api_key=settings.openai_api_key,
        temperature=0.7,
        max_retries=3,
    )


def get_fast_llm() -> ChatOpenAI:
    """GPT-4o-mini for fast drafts and scoring."""
    return ChatOpenAI(
        model=settings.openai_model_fast,
        api_key=settings.openai_api_key,
        temperature=0.3,
        max_retries=3,
    )


def get_claude_llm() -> ChatAnthropic:
    """Claude for complex reasoning and analysis."""
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0.7,
        max_retries=3,
    )


# ============================================================
# Base Agent
# ============================================================

class BaseAgent(ABC):
    """
    Base class for all 23 YouTube Automation OS agents.
    Each agent is a LangGraph state machine with quality gates.
    """

    agent_id: str = "base_agent"
    layer: int = 1
    description: str = "Base agent"
    tools: list = []

    def __init__(self):
        self.llm_premium = get_premium_llm()
        self.llm_fast = get_fast_llm()
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._graph = None

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
