from sqlalchemy import Column, String, Integer, Float, Boolean, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from models.base import TimestampMixin, UUIDMixin
from core.database import Base


class AgentStatus(str, enum.Enum):
    idle = "idle"
    running = "running"
    completed = "completed"
    error = "error"
    paused = "paused"


class AgentRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_runs"

    agent_id = Column(String(100), nullable=False, index=True)
    video_project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=True)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=True)

    status = Column(Enum(AgentStatus), default=AgentStatus.idle, nullable=False)
    input_data = Column(JSONB, default={})
    output_data = Column(JSONB)
    error_message = Column(Text)

    started_at = Column(__import__("sqlalchemy").DateTime(timezone=True))
    completed_at = Column(__import__("sqlalchemy").DateTime(timezone=True))
    duration_seconds = Column(Float)

    # Cost tracking
    tokens_used = Column(Integer, default=0)
    llm_cost_usd = Column(Float, default=0.0)

    # LangGraph checkpoint
    checkpoint_id = Column(String(255))
    graph_state = Column(JSONB, default={})

    def __repr__(self):
        return f"<AgentRun {self.agent_id} ({self.status})>"


class NicheAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "niche_analyses"

    name = Column(String(255), nullable=False)
    category = Column(String(255))
    overall_score = Column(Float)
    demand_score = Column(Float)
    competition_score = Column(Float)
    rpm_potential = Column(Float)
    production_difficulty = Column(Float)
    sponsor_potential = Column(Float)
    affiliate_potential = Column(Float)
    watch_time_potential = Column(Float)

    seasonality = Column(String(50))
    trend_direction = Column(String(20))
    estimated_monthly_rpm = Column(Float)

    top_competitors = Column(JSONB, default=[])
    content_gaps = Column(JSONB, default=[])
    opportunity_map = Column(JSONB, default={})

    raw_data = Column(JSONB, default={})


class Experiment(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "experiments"

    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    video_project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"))

    experiment_type = Column(String(50), nullable=False)  # thumbnail, title, hook, cta, upload_time
    status = Column(String(50), default="planned")

    variants = Column(JSONB, default=[])
    winner_variant_id = Column(String(255))
    statistical_significance = Column(Float)

    started_at = Column(__import__("sqlalchemy").DateTime(timezone=True))
    completed_at = Column(__import__("sqlalchemy").DateTime(timezone=True))

    # Relationships
    channel = relationship("Channel", back_populates="experiments")

    def __repr__(self):
        return f"<Experiment {self.experiment_type} ({self.status})>"


# Import relationship fix
from sqlalchemy.orm import relationship
NicheAnalysis.channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=True)
