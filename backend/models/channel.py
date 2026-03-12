from sqlalchemy import Column, String, Integer, Float, Boolean, Text, ARRAY, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from models.base import TimestampMixin, UUIDMixin
from core.database import Base


class YPPStatus(str, enum.Enum):
    not_eligible = "not_eligible"
    pending = "pending"
    active = "active"
    suspended = "suspended"


class Channel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "channels"

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    niche = Column(String(255), nullable=False)
    description = Column(Text)
    youtube_channel_id = Column(String(255), unique=True)

    # Metrics
    subscribers = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    watch_hours = Column(Float, default=0.0)
    monthly_revenue = Column(Float, default=0.0)

    # Status
    ypp_status = Column(Enum(YPPStatus), default=YPPStatus.not_eligible)
    is_active = Column(Boolean, default=True)

    # Scores (0-100)
    compliance_score = Column(Float, default=0.0)
    originality_score = Column(Float, default=0.0)
    brand_consistency_score = Column(Float, default=0.0)

    # Strategy
    content_pillars = Column(ARRAY(String), default=[])
    thumbnail_style = Column(String(255))
    voice_persona_id = Column(UUID(as_uuid=True))

    # Blueprint JSON (from Channel Architect Agent)
    blueprint = Column(JSONB, default={})

    # Relationships
    videos = relationship("VideoProject", back_populates="channel", lazy="dynamic")
    experiments = relationship("Experiment", back_populates="channel", lazy="dynamic")
    niche_analyses = relationship("NicheAnalysis", back_populates="channel", lazy="dynamic")

    def __repr__(self):
        return f"<Channel {self.name} ({self.slug})>"
