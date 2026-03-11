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
