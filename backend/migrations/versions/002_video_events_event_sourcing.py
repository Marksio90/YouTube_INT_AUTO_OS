"""Add video_events table for Event Sourcing

Revision ID: 002
Revises: 001
Create Date: 2026-03-12

Adds:
- video_events table (append-only event log)
- Indexes for fast event replay and analytics queries
- EventType enum with all 30+ domain events
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create EventType enum
    event_type_enum = sa.Enum(
        "video.created",
        "video.stage_advanced",
        "video.published",
        "video.rejected",
        "script.generated",
        "script.approved",
        "script.revised",
        "hook.generated",
        "hook.critiqued",
        "hook.refined",
        "hook.approved",
        "hook.rejected",
        "retention.analyzed",
        "retention.devices_injected",
        "retention.rescored",
        "retention.gate_passed",
        "retention.gate_failed",
        "tts.generated",
        "thumbnail.generated",
        "storyboard.created",
        "video.rendered",
        "video.render_chunk",
        "seo.optimized",
        "originality.checked",
        "compliance.passed",
        "compliance.failed",
        "analytics.snapshot",
        "analytics.retention_curve",
        "analytics.low_retention",
        "analytics.high_retention",
        "experiment.started",
        "experiment.variant_selected",
        "experiment.concluded",
        "agent.run_started",
        "agent.run_completed",
        "agent.run_failed",
        "model_router.decision",
        name="eventtype",
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    # Create video_events table
    op.create_table(
        "video_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "video_project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("video_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Emitter metadata
        sa.Column("agent_id", sa.String(100)),
        sa.Column("agent_layer", sa.String(10)),
        sa.Column("run_id", sa.String(255)),
        # Event payload and quality snapshot (immutable JSONB)
        sa.Column("payload", JSONB, nullable=False, server_default="'{}'"),
        sa.Column("quality_snapshot", JSONB, server_default="'{}'"),
        # Causality chain
        sa.Column(
            "caused_by_event_id",
            UUID(as_uuid=True),
            sa.ForeignKey("video_events.id"),
            nullable=True,
        ),
    )

    # Indexes for common query patterns
    op.create_index(
        "ix_video_events_project_time",
        "video_events",
        ["video_project_id", "occurred_at"],
    )
    op.create_index(
        "ix_video_events_type_time",
        "video_events",
        ["event_type", "occurred_at"],
    )
    op.create_index(
        "ix_video_events_agent_type",
        "video_events",
        ["agent_id", "event_type"],
    )
    # Single-column indexes for filtering
    op.create_index(
        "ix_video_events_video_project_id",
        "video_events",
        ["video_project_id"],
    )
    op.create_index(
        "ix_video_events_event_type",
        "video_events",
        ["event_type"],
    )
    op.create_index(
        "ix_video_events_occurred_at",
        "video_events",
        ["occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_video_events_occurred_at", table_name="video_events")
    op.drop_index("ix_video_events_event_type", table_name="video_events")
    op.drop_index("ix_video_events_video_project_id", table_name="video_events")
    op.drop_index("ix_video_events_agent_type", table_name="video_events")
    op.drop_index("ix_video_events_type_time", table_name="video_events")
    op.drop_index("ix_video_events_project_time", table_name="video_events")
    op.drop_table("video_events")
    sa.Enum(name="eventtype").drop(op.get_bind(), checkfirst=True)
