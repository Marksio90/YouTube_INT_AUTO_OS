"""
Event Sourcing — VideoEvent model.

Instead of mutating VideoProject rows directly, every significant state change
is appended as an immutable event. This gives us:

1. Time-travel debugging: replay events to reconstruct state at any point
2. Agent decision auditing: WHY did an agent reject/approve a hook?
3. A/B test history: trace which hook variant led to which retention score
4. Closed-loop learning: join events with VideoAnalytics for training signal

Usage:
    from models.events import VideoEvent, EventType
    from services.event_service import emit_event

    await emit_event(
        video_project_id=video_id,
        event_type=EventType.HOOK_GENERATED,
        agent_id="hook_specialist",
        payload={"hook_score": 8.7, "pattern": "curiosity_gap"},
    )

Event sourcing pattern:
    Write: append-only INSERT into video_events
    Read:  query by video_project_id ORDER BY occurred_at
    Rebuild state: fold events left-to-right
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Index, DateTime, Enum as SAEnum, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.database import Base


# ------------------------------------------------------------------ #
# Event Type Catalogue
# Every domain event the system can emit — extend freely, never delete.
# ------------------------------------------------------------------ #

class EventType(str, enum.Enum):
    # Video lifecycle ────────────────────────────────────────────
    VIDEO_CREATED           = "video.created"
    VIDEO_STAGE_ADVANCED    = "video.stage_advanced"
    VIDEO_PUBLISHED         = "video.published"
    VIDEO_REJECTED          = "video.rejected"

    # Script events ──────────────────────────────────────────────
    SCRIPT_GENERATED        = "script.generated"
    SCRIPT_APPROVED         = "script.approved"
    SCRIPT_REVISED          = "script.revised"

    # Hook events ────────────────────────────────────────────────
    HOOK_GENERATED          = "hook.generated"
    HOOK_CRITIQUED          = "hook.critiqued"        # Adversarial Critic ran
    HOOK_REFINED            = "hook.refined"          # Refiner addressed critique
    HOOK_APPROVED           = "hook.approved"         # gate_passed=True
    HOOK_REJECTED           = "hook.rejected"         # gate_passed=False, aborted

    # Retention events ───────────────────────────────────────────
    RETENTION_ANALYZED      = "retention.analyzed"
    RETENTION_DEVICES_INJECTED = "retention.devices_injected"
    RETENTION_RESCORED      = "retention.rescored"    # After reflection cycle
    RETENTION_GATE_PASSED   = "retention.gate_passed"
    RETENTION_GATE_FAILED   = "retention.gate_failed"

    # Production events ──────────────────────────────────────────
    TTS_GENERATED           = "tts.generated"
    THUMBNAIL_GENERATED     = "thumbnail.generated"
    STORYBOARD_CREATED      = "storyboard.created"
    VIDEO_RENDERED          = "video.rendered"
    VIDEO_RENDER_CHUNK      = "video.render_chunk"    # Parallel chunk render

    # SEO & compliance ───────────────────────────────────────────
    SEO_OPTIMIZED           = "seo.optimized"
    ORIGINALITY_CHECKED     = "originality.checked"
    COMPLIANCE_PASSED       = "compliance.passed"
    COMPLIANCE_FAILED       = "compliance.failed"

    # Analytics feedback loop (closed-loop learning) ─────────────
    ANALYTICS_SNAPSHOT      = "analytics.snapshot"   # YT data pulled at T+2h/24h/...
    RETENTION_CURVE_RECEIVED = "analytics.retention_curve"
    LOW_RETENTION_SIGNAL    = "analytics.low_retention"   # Triggers agent learning
    HIGH_RETENTION_SIGNAL   = "analytics.high_retention"  # Positive reinforcement

    # Experiment events ──────────────────────────────────────────
    EXPERIMENT_STARTED      = "experiment.started"
    EXPERIMENT_VARIANT_SELECTED = "experiment.variant_selected"
    EXPERIMENT_CONCLUDED    = "experiment.concluded"

    # System / agent meta ────────────────────────────────────────
    AGENT_RUN_STARTED       = "agent.run_started"
    AGENT_RUN_COMPLETED     = "agent.run_completed"
    AGENT_RUN_FAILED        = "agent.run_failed"
    MODEL_ROUTER_DECISION   = "model_router.decision"  # Which LLM was chosen + why


# ------------------------------------------------------------------ #
# VideoEvent — append-only event store row
# ------------------------------------------------------------------ #

class VideoEvent(Base):
    """
    Immutable event record. Never update or delete rows.
    Use video_project_id + occurred_at to replay history.
    """
    __tablename__ = "video_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Core event fields
    video_project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("video_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(SAEnum(EventType), nullable=False, index=True)
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Who emitted this event
    agent_id = Column(String(100))          # e.g. "hook_specialist"
    agent_layer = Column(String(10))        # e.g. "3"
    run_id = Column(String(255))            # AgentRun.id that triggered this

    # What happened
    payload = Column(JSONB, nullable=False, default=dict)
    """
    Payload examples by event_type:

    HOOK_CRITIQUED:
        {"verdict": "marginal", "approved_count": 2,
         "fatal_flaws": [...], "critique_summary": "..."}

    RETENTION_RESCORED:
        {"cycle": 1, "prev_avg": 48.0, "new_avg": 57.2,
         "improvement": "+9.2%", "gate_passed": true}

    ANALYTICS_SNAPSHOT:
        {"youtube_video_id": "abc123", "views": 12000,
         "avg_retention_pct": 42.0, "ctr": 0.054,
         "retention_curve": [...]}

    LOW_RETENTION_SIGNAL:
        {"threshold_pct": 45.0, "actual_pct": 38.2,
         "drop_at_30s": true, "hook_variant_used": "curiosity_gap",
         "learning_note": "Curiosity gap hooks underperform in finance niche"}

    MODEL_ROUTER_DECISION:
        {"task_type": "critique_hooks", "complexity": "expert",
         "model_id": "claude-sonnet-4-6", "cost_tier": "high",
         "reason": "Adversarial critique requires expert reasoning"}
    """

    # Causality chain (for debugging: "what triggered this?")
    caused_by_event_id = Column(UUID(as_uuid=True), ForeignKey("video_events.id"))

    # Quality snapshot at time of event (denormalized for fast analytics)
    quality_snapshot = Column(JSONB, default=dict)
    """
    e.g. {"hook_score": 8.7, "retention_avg": 57.2, "originality": 91.0}
    Stored as-is at event time — immutable historical record.
    """

    # Relationships
    video_project = relationship("VideoProject", back_populates="events")
    caused_by = relationship("VideoEvent", remote_side=[id])

    # ── Indexes ──────────────────────────────────────────────────
    __table_args__ = (
        # Fast replay: all events for a video in order
        Index("ix_video_events_project_time", "video_project_id", "occurred_at"),
        # Fast analytics queries by event type + time range
        Index("ix_video_events_type_time", "event_type", "occurred_at"),
        # Agent performance tracking
        Index("ix_video_events_agent_type", "agent_id", "event_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<VideoEvent {self.event_type.value} "
            f"video={self.video_project_id} agent={self.agent_id}>"
        )

    @classmethod
    def create(
        cls,
        video_project_id: str,
        event_type: EventType,
        payload: dict,
        agent_id: str | None = None,
        agent_layer: str | None = None,
        run_id: str | None = None,
        quality_snapshot: dict | None = None,
        caused_by_event_id: str | None = None,
    ) -> "VideoEvent":
        """Factory method for creating events (avoids import confusion)."""
        return cls(
            video_project_id=video_project_id,
            event_type=event_type,
            payload=payload,
            agent_id=agent_id,
            agent_layer=agent_layer,
            run_id=run_id,
            quality_snapshot=quality_snapshot or {},
            caused_by_event_id=caused_by_event_id,
        )
