from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ARRAY, Enum, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import enum
from models.base import TimestampMixin, UUIDMixin
from core.database import Base


class PipelineStage(str, enum.Enum):
    idea = "idea"
    script = "script"
    voice = "voice"
    video = "video"
    thumbnail = "thumbnail"
    seo = "seo"
    review = "review"
    scheduled = "scheduled"
    published = "published"


class ContentFormat(str, enum.Enum):
    long_form = "long_form"
    shorts = "shorts"
    podcast_video = "podcast_video"
    clips = "clips"
    community_post = "community_post"


class RiskLevel(str, enum.Enum):
    green = "green"
    yellow = "yellow"
    red = "red"


class VideoProject(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "video_projects"

    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    title = Column(String(500), nullable=False)
    stage = Column(Enum(PipelineStage), default=PipelineStage.idea, nullable=False)
    format = Column(Enum(ContentFormat), default=ContentFormat.long_form)
    niche = Column(String(255))
    target_keywords = Column(ARRAY(String), default=[])

    # Quality Scores
    hook_score = Column(Float)
    originality_score = Column(Float)
    thumbnail_score = Column(Float)
    seo_score = Column(Float)
    overall_quality_score = Column(Float)
    compliance_risk = Column(Enum(RiskLevel), default=RiskLevel.green)

    # Agent tracking
    assigned_agents = Column(ARRAY(String), default=[])

    # Assets
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"))
    voice_track_url = Column(String(1000))
    thumbnail_urls = Column(ARRAY(String), default=[])
    video_url = Column(String(1000))
    published_url = Column(String(1000))

    # Schedule
    scheduled_for = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))

    # Duration
    estimated_duration_seconds = Column(Integer)
    actual_duration_seconds = Column(Integer)

    # Embedding for similarity check (1536-dim for text-embedding-3-large)
    content_embedding = Column(Vector(1536))

    # Metadata
    seo_metadata = Column(JSONB, default={})
    agent_outputs = Column(JSONB, default={})

    # Relationships
    channel = relationship("Channel", back_populates="videos")
    script = relationship("Script", back_populates="video", foreign_keys=[script_id])
    compliance_report = relationship("ComplianceReport", back_populates="video", uselist=False)
    analytics = relationship("VideoAnalytics", back_populates="video", uselist=True, order_by="VideoAnalytics.created_at")
    events = relationship(
        "VideoEvent",
        back_populates="video_project",
        order_by="VideoEvent.occurred_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<VideoProject {self.title[:50]} ({self.stage})>"


class Script(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scripts"

    video_project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"))
    title = Column(String(500))

    # 6-part structure (Module II)
    hook = Column(Text)
    intro = Column(Text)
    problem = Column(Text)
    deepening = Column(Text)
    value = Column(Text)
    cta = Column(Text)
    full_text = Column(Text)

    word_count = Column(Integer)
    estimated_duration_seconds = Column(Integer)

    # Scores
    hook_score = Column(Float)
    retention_score = Column(Float)
    naturality_score = Column(Float)
    originality_score = Column(Float)

    version = Column(Integer, default=1)

    # Hook variants (from Hook Specialist Agent)
    hook_variants = Column(JSONB, default=[])

    # Embedding
    content_embedding = Column(Vector(1536))

    video = relationship("VideoProject", back_populates="script", foreign_keys=[VideoProject.script_id])

    def __repr__(self):
        return f"<Script v{self.version} for {self.video_project_id}>"


class ComplianceReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "compliance_reports"

    video_project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), unique=True)

    originality_score = Column(Float, default=100.0)
    similarity_to_other_videos = Column(Float, default=0.0)
    template_overuse_risk = Column(Enum(RiskLevel), default=RiskLevel.green)
    copyright_risk = Column(Enum(RiskLevel), default=RiskLevel.green)

    ai_disclosure_required = Column(Boolean, default=False)
    ai_disclosure_set = Column(Boolean, default=False)
    sponsor_disclosure_required = Column(Boolean, default=False)
    sponsor_disclosure_set = Column(Boolean, default=False)

    ypp_safe = Column(Boolean, default=True)

    issues = Column(JSONB, default=[])
    recommendations = Column(ARRAY(String), default=[])

    video = relationship("VideoProject", back_populates="compliance_report")


class VideoAnalytics(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "video_analytics"

    # No unique=True — multiple analytics snapshots allowed per video (time-series tracking)
    video_project_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False, index=True)
    youtube_video_id = Column(String(255))

    views = Column(Integer, default=0)
    watch_time_minutes = Column(Float, default=0.0)
    avg_view_duration_seconds = Column(Float, default=0.0)
    avg_retention_percent = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    rpm = Column(Float, default=0.0)

    retention_curve = Column(JSONB, default=[])
    traffic_sources = Column(JSONB, default=[])
    demographics = Column(JSONB, default={})

    video = relationship("VideoProject", back_populates="analytics", foreign_keys=[video_project_id])


class ComplianceAlert(Base, UUIDMixin, TimestampMixin):
    """Cross-video similarity alert generated by weekly compliance scan."""
    __tablename__ = "compliance_alerts"

    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False, index=True)
    video_a_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    video_b_id = Column(UUID(as_uuid=True), ForeignKey("video_projects.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    alert_type = Column(String(50), nullable=False, default="high_similarity")
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("channel_id", "video_a_id", "video_b_id", name="uq_compliance_alert_pair"),
        Index("ix_compliance_alerts_channel_id", "channel_id"),
    )
