from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class AgentInfo(BaseModel):
    id: str
    name: str
    layer: int
    description: str
    status: str
    tasks_completed: int
    success_rate: float
    avg_duration_seconds: float
    tools: List[str]


class AgentRunRequest(BaseModel):
    input_data: Dict[str, Any] = Field(default_factory=dict)
    video_project_id: Optional[UUID] = None
    channel_id: Optional[UUID] = None
    async_mode: bool = Field(default=True)


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    tokens_used: int
    llm_cost_usd: float
    created_at: datetime


class NicheAnalyzeRequest(BaseModel):
    niche_name: str = Field(..., min_length=2, max_length=255)
    category: Optional[str] = None
    target_country: str = "PL"
    language: str = "pl"


class NicheAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: Optional[str]
    overall_score: float
    demand_score: float
    competition_score: float
    rpm_potential: float
    production_difficulty: float
    sponsor_potential: float
    affiliate_potential: float
    watch_time_potential: float
    seasonality: Optional[str]
    trend_direction: Optional[str]
    estimated_monthly_rpm: Optional[float]
    top_competitors: List[str]
    content_gaps: List[str]
    opportunity_map: Dict[str, Any]
    created_at: datetime


class ExperimentCreate(BaseModel):
    channel_id: UUID
    video_project_id: Optional[UUID] = None
    experiment_type: str = Field(..., pattern="^(thumbnail|title|hook|cta|upload_time|video_length)$")
    variants: List[Dict[str, Any]] = Field(..., min_length=2, max_length=4)


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel_id: UUID
    video_project_id: Optional[UUID]
    experiment_type: str
    status: str
    variants: List[Dict[str, Any]]
    winner_variant_id: Optional[str]
    statistical_significance: Optional[float]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
