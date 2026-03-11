"""Initial schema with pgvector

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # channels
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False, unique=True),
        sa.Column('niche', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('youtube_channel_id', sa.String(255), unique=True),
        sa.Column('subscribers', sa.Integer(), default=0),
        sa.Column('total_views', sa.Integer(), default=0),
        sa.Column('watch_hours', sa.Float(), default=0.0),
        sa.Column('monthly_revenue', sa.Float(), default=0.0),
        sa.Column('ypp_status', sa.String(50), default='not_eligible'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('compliance_score', sa.Float(), default=0.0),
        sa.Column('originality_score', sa.Float(), default=0.0),
        sa.Column('brand_consistency_score', sa.Float(), default=0.0),
        sa.Column('content_pillars', postgresql.ARRAY(sa.String())),
        sa.Column('thumbnail_style', sa.String(255)),
        sa.Column('voice_persona_id', postgresql.UUID(as_uuid=True)),
        sa.Column('blueprint', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # video_projects
    op.create_table(
        'video_projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('stage', sa.String(50), default='idea'),
        sa.Column('format', sa.String(50), default='long_form'),
        sa.Column('niche', sa.String(255)),
        sa.Column('target_keywords', postgresql.ARRAY(sa.String())),
        sa.Column('hook_score', sa.Float()),
        sa.Column('originality_score', sa.Float()),
        sa.Column('thumbnail_score', sa.Float()),
        sa.Column('seo_score', sa.Float()),
        sa.Column('overall_quality_score', sa.Float()),
        sa.Column('compliance_risk', sa.String(20), default='green'),
        sa.Column('assigned_agents', postgresql.ARRAY(sa.String())),
        sa.Column('script_id', postgresql.UUID(as_uuid=True)),
        sa.Column('voice_track_url', sa.String(1000)),
        sa.Column('thumbnail_urls', postgresql.ARRAY(sa.String())),
        sa.Column('video_url', sa.String(1000)),
        sa.Column('published_url', sa.String(1000)),
        sa.Column('scheduled_for', sa.DateTime(timezone=True)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('estimated_duration_seconds', sa.Integer()),
        sa.Column('actual_duration_seconds', sa.Integer()),
        # Vector embedding (1536 dimensions for text-embedding-3-large)
        sa.Column('content_embedding', sa.Text()),  # Will be cast to vector(1536) via raw SQL
        sa.Column('seo_metadata', postgresql.JSONB()),
        sa.Column('agent_outputs', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id']),
    )
    # Add vector column separately via raw SQL
    op.execute("ALTER TABLE video_projects ADD COLUMN IF NOT EXISTS content_embedding_vec vector(1536)")
    op.execute("CREATE INDEX IF NOT EXISTS video_projects_embedding_idx ON video_projects USING ivfflat (content_embedding_vec vector_cosine_ops) WITH (lists = 100)")

    # scripts
    op.create_table(
        'scripts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_project_id', postgresql.UUID(as_uuid=True)),
        sa.Column('title', sa.String(500)),
        sa.Column('hook', sa.Text()),
        sa.Column('intro', sa.Text()),
        sa.Column('problem', sa.Text()),
        sa.Column('deepening', sa.Text()),
        sa.Column('value', sa.Text()),
        sa.Column('cta', sa.Text()),
        sa.Column('full_text', sa.Text()),
        sa.Column('word_count', sa.Integer()),
        sa.Column('estimated_duration_seconds', sa.Integer()),
        sa.Column('hook_score', sa.Float()),
        sa.Column('retention_score', sa.Float()),
        sa.Column('naturality_score', sa.Float()),
        sa.Column('originality_score', sa.Float()),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('hook_variants', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['video_project_id'], ['video_projects.id']),
    )
    op.execute("ALTER TABLE scripts ADD COLUMN IF NOT EXISTS content_embedding vector(1536)")
    op.execute("CREATE INDEX IF NOT EXISTS scripts_embedding_idx ON scripts USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100)")

    # compliance_reports
    op.create_table(
        'compliance_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_project_id', postgresql.UUID(as_uuid=True), unique=True),
        sa.Column('originality_score', sa.Float(), default=100.0),
        sa.Column('similarity_to_other_videos', sa.Float(), default=0.0),
        sa.Column('template_overuse_risk', sa.String(20), default='green'),
        sa.Column('copyright_risk', sa.String(20), default='green'),
        sa.Column('ai_disclosure_required', sa.Boolean(), default=False),
        sa.Column('ai_disclosure_set', sa.Boolean(), default=False),
        sa.Column('sponsor_disclosure_required', sa.Boolean(), default=False),
        sa.Column('sponsor_disclosure_set', sa.Boolean(), default=False),
        sa.Column('ypp_safe', sa.Boolean(), default=True),
        sa.Column('issues', postgresql.JSONB()),
        sa.Column('recommendations', postgresql.ARRAY(sa.String())),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['video_project_id'], ['video_projects.id']),
    )

    # video_analytics
    op.create_table(
        'video_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_project_id', postgresql.UUID(as_uuid=True), unique=True),
        sa.Column('youtube_video_id', sa.String(255)),
        sa.Column('views', sa.Integer(), default=0),
        sa.Column('watch_time_minutes', sa.Float(), default=0.0),
        sa.Column('avg_view_duration_seconds', sa.Float(), default=0.0),
        sa.Column('avg_retention_percent', sa.Float(), default=0.0),
        sa.Column('ctr', sa.Float(), default=0.0),
        sa.Column('likes', sa.Integer(), default=0),
        sa.Column('comments', sa.Integer(), default=0),
        sa.Column('shares', sa.Integer(), default=0),
        sa.Column('revenue', sa.Float(), default=0.0),
        sa.Column('rpm', sa.Float(), default=0.0),
        sa.Column('retention_curve', postgresql.JSONB()),
        sa.Column('traffic_sources', postgresql.JSONB()),
        sa.Column('demographics', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['video_project_id'], ['video_projects.id']),
    )

    # agent_runs
    op.create_table(
        'agent_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(100), nullable=False, index=True),
        sa.Column('video_project_id', postgresql.UUID(as_uuid=True)),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status', sa.String(50), default='idle'),
        sa.Column('input_data', postgresql.JSONB()),
        sa.Column('output_data', postgresql.JSONB()),
        sa.Column('error_message', sa.Text()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('duration_seconds', sa.Float()),
        sa.Column('tokens_used', sa.Integer(), default=0),
        sa.Column('llm_cost_usd', sa.Float(), default=0.0),
        sa.Column('checkpoint_id', sa.String(255)),
        sa.Column('graph_state', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # niche_analyses
    op.create_table(
        'niche_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(255)),
        sa.Column('overall_score', sa.Float()),
        sa.Column('demand_score', sa.Float()),
        sa.Column('competition_score', sa.Float()),
        sa.Column('rpm_potential', sa.Float()),
        sa.Column('production_difficulty', sa.Float()),
        sa.Column('sponsor_potential', sa.Float()),
        sa.Column('affiliate_potential', sa.Float()),
        sa.Column('watch_time_potential', sa.Float()),
        sa.Column('seasonality', sa.String(50)),
        sa.Column('trend_direction', sa.String(20)),
        sa.Column('estimated_monthly_rpm', sa.Float()),
        sa.Column('top_competitors', postgresql.JSONB()),
        sa.Column('content_gaps', postgresql.JSONB()),
        sa.Column('opportunity_map', postgresql.JSONB()),
        sa.Column('raw_data', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # experiments
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('channel_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('video_project_id', postgresql.UUID(as_uuid=True)),
        sa.Column('experiment_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), default='planned'),
        sa.Column('variants', postgresql.JSONB()),
        sa.Column('winner_variant_id', sa.String(255)),
        sa.Column('statistical_significance', sa.Float()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id']),
    )


def downgrade() -> None:
    op.drop_table('experiments')
    op.drop_table('niche_analyses')
    op.drop_table('agent_runs')
    op.drop_table('video_analytics')
    op.drop_table('compliance_reports')
    op.drop_table('scripts')
    op.drop_table('video_projects')
    op.drop_table('channels')
