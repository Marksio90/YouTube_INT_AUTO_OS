"""
Langfuse LLM Observability Integration
Tracks all LLM calls (GPT-4o, GPT-4o-mini, Claude) made by agents.

Features:
- Automatic tracing of LangChain/LangGraph agent runs
- Cost tracking per agent and per video project
- Quality scoring correlations
- Prompt/response logging for debugging

Usage:
    from core.langfuse import get_langfuse_callback, langfuse_client

    # In agent LLM factory:
    callbacks = get_langfuse_callback(trace_name="niche_hunter", metadata={...})
    llm = get_premium_llm(callbacks=callbacks)
"""
import structlog
from typing import Optional, Dict, Any, List

from core.config import settings

logger = structlog.get_logger(__name__)

# Global Langfuse client (None if not configured)
_langfuse_client = None
_langfuse_available = False


def _init_langfuse():
    """Initialize Langfuse client if credentials are configured."""
    global _langfuse_client, _langfuse_available

    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.info("Langfuse not configured — LLM monitoring disabled")
        return

    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        _langfuse_available = True
        logger.info("Langfuse initialized", host=settings.langfuse_host)
    except ImportError:
        logger.warning("langfuse package not installed — pip install langfuse")
    except Exception as e:
        logger.error("Langfuse initialization failed", error=str(e))


# Initialize on import
_init_langfuse()


def get_langfuse_client():
    """Return the initialized Langfuse client, or None if not available."""
    return _langfuse_client if _langfuse_available else None


def get_langfuse_callbacks(
    trace_name: str,
    metadata: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> list:
    """
    Create Langfuse LangChain callback handlers for tracing an agent run.
    Returns empty list if Langfuse is not configured.

    Args:
        trace_name: Human-readable name for this trace (e.g. "niche_hunter_run")
        metadata: Extra context dict (e.g. {"channel_id": "...", "video_id": "..."})
        session_id: Group traces by session (e.g. video_project_id)
        user_id: Optionally associate trace with a user
        tags: List of tags for filtering (e.g. ["production", "layer_1"])
    """
    if not _langfuse_available:
        return []

    try:
        from langfuse.callback import CallbackHandler
        handler = CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
            trace_name=trace_name,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
            tags=tags or [],
        )
        return [handler]
    except ImportError:
        return []
    except Exception as e:
        logger.warning("Failed to create Langfuse callback", error=str(e))
        return []


def create_trace(
    name: str,
    input_data: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    session_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
):
    """
    Create a manual Langfuse trace for non-LangChain operations
    (e.g. Whisper transcription, DALL-E generation, ElevenLabs TTS).
    Returns trace object or None if Langfuse not configured.
    """
    if not _langfuse_available or not _langfuse_client:
        return None

    try:
        return _langfuse_client.trace(
            name=name,
            input=input_data or {},
            metadata=metadata or {},
            session_id=session_id,
            tags=tags or [],
        )
    except Exception as e:
        logger.warning("Failed to create Langfuse trace", error=str(e))
        return None


def flush():
    """Flush all pending Langfuse events (call on app shutdown)."""
    if _langfuse_available and _langfuse_client:
        try:
            _langfuse_client.flush()
        except Exception as e:
            logger.warning("Langfuse flush failed", error=str(e))


def is_enabled() -> bool:
    """Return True if Langfuse monitoring is active."""
    return _langfuse_available


# ============================================================
# Closed-Loop Feedback — YouTube Analytics → Langfuse Scores
# ============================================================

def score_session_retention(
    session_id: str,
    avg_retention_pct: float,
    drop_at_30s: bool = False,
    hook_variant: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Submit a YouTube retention outcome as a Langfuse score on the session
    that produced the video.

    This closes the feedback loop:
      Agent run (session_id=video_project_id)
        → Langfuse trace
          → YouTube Analytics pulled at T+24h
            → score_session_retention(session_id=video_project_id, avg=42%)
              → Langfuse shows score "youtube_retention=0.42" on that trace

    Over time, low-scored prompts can be identified and updated.

    Args:
        session_id:         video_project_id (used as Langfuse session_id)
        avg_retention_pct:  0-100 float from YouTube Analytics
        drop_at_30s:        True if hook caused early drop (first 30s)
        hook_variant:       Pattern used (e.g. "curiosity_gap")
        extra:              Additional metadata to attach as comment JSON
    """
    if not _langfuse_available or not _langfuse_client:
        return

    comment_parts = [f"avg_retention={avg_retention_pct:.1f}%"]
    if drop_at_30s:
        comment_parts.append("early_drop=true (hook may be weak)")
    if hook_variant:
        comment_parts.append(f"hook_variant={hook_variant}")
    if extra:
        import json as _json
        comment_parts.append(_json.dumps(extra, ensure_ascii=False)[:200])

    try:
        _langfuse_client.score(
            name="youtube_retention",
            value=round(avg_retention_pct / 100.0, 4),
            comment=" | ".join(comment_parts),
            session_id=session_id,
        )

        # Also submit binary pass/fail for easy filtering
        _langfuse_client.score(
            name="retention_gate_real",
            value=1.0 if avg_retention_pct >= 45.0 else 0.0,
            comment=f"Gate threshold: 45% | actual: {avg_retention_pct:.1f}%",
            session_id=session_id,
        )

        logger.info(
            "Langfuse retention feedback scored",
            session_id=session_id,
            retention=avg_retention_pct,
        )
    except Exception as e:
        logger.warning("Langfuse score submission failed", error=str(e))


def score_session_ctr(
    session_id: str,
    ctr_pct: float,
    title_variant: Optional[str] = None,
    thumbnail_style: Optional[str] = None,
) -> None:
    """
    Submit Click-Through Rate as a Langfuse score.
    Feeds back into title_architect and thumbnail_psychology agents.
    """
    if not _langfuse_available or not _langfuse_client:
        return

    comment = f"ctr={ctr_pct:.2f}%"
    if title_variant:
        comment += f" | title_variant={title_variant}"
    if thumbnail_style:
        comment += f" | thumbnail_style={thumbnail_style}"

    try:
        _langfuse_client.score(
            name="youtube_ctr",
            value=round(ctr_pct / 100.0, 4),
            comment=comment,
            session_id=session_id,
        )
        logger.info(
            "Langfuse CTR feedback scored",
            session_id=session_id,
            ctr=ctr_pct,
        )
    except Exception as e:
        logger.warning("Langfuse CTR score failed", error=str(e))


def score_model_router_decision(
    session_id: str,
    task_type: str,
    model_id: str,
    cost_tier: str,
    quality_gate_passed: bool,
) -> None:
    """
    Record a Model Router decision as a Langfuse score.
    Enables cost vs. quality analysis: which tasks need expensive models?
    """
    if not _langfuse_available or not _langfuse_client:
        return

    cost_map = {"very_low": 0.02, "low": 0.10, "medium": 0.50, "high": 1.0}

    try:
        _langfuse_client.score(
            name="model_cost_tier",
            value=cost_map.get(cost_tier, 0.5),
            comment=(
                f"task={task_type} | model={model_id} | "
                f"gate_passed={quality_gate_passed}"
            ),
            session_id=session_id,
        )
    except Exception as e:
        logger.warning("Langfuse model router score failed", error=str(e))
