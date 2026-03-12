"""
Event Service — append-only writer for VideoEvent (Event Sourcing).

Provides a thin async wrapper over the DB write + optional Langfuse scoring
for analytics feedback events.

Usage:
    from services.event_service import emit_event
    from models.events import EventType

    await emit_event(
        db=db,
        video_project_id=video_id,
        event_type=EventType.HOOK_CRITIQUED,
        agent_id="hook_specialist",
        agent_layer="3",
        run_id=run_id,
        payload={"verdict": "marginal", "approved_count": 2},
        quality_snapshot={"hook_score": 7.8},
    )
"""
from __future__ import annotations

from typing import Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.events import VideoEvent, EventType

logger = structlog.get_logger(__name__)


async def emit_event(
    db: AsyncSession,
    video_project_id: str,
    event_type: EventType,
    payload: dict,
    agent_id: Optional[str] = None,
    agent_layer: Optional[str] = None,
    run_id: Optional[str] = None,
    quality_snapshot: Optional[dict] = None,
    caused_by_event_id: Optional[str] = None,
) -> VideoEvent:
    """
    Append an immutable event to the video_events table.
    Never raises — logs errors and returns None on failure.
    """
    event = VideoEvent.create(
        video_project_id=video_project_id,
        event_type=event_type,
        payload=payload,
        agent_id=agent_id,
        agent_layer=agent_layer,
        run_id=run_id,
        quality_snapshot=quality_snapshot or {},
        caused_by_event_id=caused_by_event_id,
    )
    try:
        db.add(event)
        await db.flush()   # Get the ID without committing the outer transaction
        logger.debug(
            "Event emitted",
            event_type=event_type.value,
            video_project_id=str(video_project_id),
            agent_id=agent_id,
        )
    except Exception as e:
        logger.error(
            "Failed to emit event",
            event_type=event_type.value,
            error=str(e),
        )
    return event


async def emit_analytics_feedback(
    db: AsyncSession,
    video_project_id: str,
    youtube_video_id: str,
    analytics_data: dict,
    caused_by_event_id: Optional[str] = None,
) -> list[VideoEvent]:
    """
    Emit analytics feedback events and trigger closed-loop learning signals.

    Emits:
    - ANALYTICS_SNAPSHOT always
    - LOW_RETENTION_SIGNAL if avg_retention < 45%
    - HIGH_RETENTION_SIGNAL if avg_retention >= 65%
    """
    events: list[VideoEvent] = []

    avg_retention = analytics_data.get("avg_retention_pct", 0.0)
    retention_curve = analytics_data.get("retention_curve", [])

    # Always emit the raw snapshot
    snapshot_event = await emit_event(
        db=db,
        video_project_id=video_project_id,
        event_type=EventType.ANALYTICS_SNAPSHOT,
        payload={
            "youtube_video_id": youtube_video_id,
            "views": analytics_data.get("views", 0),
            "avg_retention_pct": avg_retention,
            "ctr": analytics_data.get("ctr", 0.0),
            "watch_time_minutes": analytics_data.get("watch_time_minutes", 0.0),
            "retention_curve": retention_curve[:20],  # Store first 20 points
        },
        caused_by_event_id=caused_by_event_id,
    )
    events.append(snapshot_event)

    # Emit retention curve if available
    if retention_curve:
        curve_event = await emit_event(
            db=db,
            video_project_id=video_project_id,
            event_type=EventType.RETENTION_CURVE_RECEIVED,
            payload={
                "curve": retention_curve,
                "drop_at_30s": _detect_early_drop(retention_curve, second=30),
                "drop_at_50pct": _detect_midpoint_cliff(retention_curve),
            },
            caused_by_event_id=snapshot_event.id if snapshot_event else None,
        )
        events.append(curve_event)

    # Closed-loop learning signals
    if avg_retention < 45.0:
        signal = await emit_event(
            db=db,
            video_project_id=video_project_id,
            event_type=EventType.LOW_RETENTION_SIGNAL,
            payload={
                "threshold_pct": 45.0,
                "actual_pct": avg_retention,
                "drop_at_30s": _detect_early_drop(retention_curve, second=30),
                "learning_note": (
                    "Hook or intro likely underperformed — "
                    "check hook variant and first 60s pacing"
                ),
            },
            quality_snapshot={"avg_retention_pct": avg_retention},
            caused_by_event_id=snapshot_event.id if snapshot_event else None,
        )
        events.append(signal)
        # Annotate Langfuse trace if available
        _annotate_langfuse_low_retention(video_project_id, avg_retention)

    elif avg_retention >= 65.0:
        signal = await emit_event(
            db=db,
            video_project_id=video_project_id,
            event_type=EventType.HIGH_RETENTION_SIGNAL,
            payload={
                "threshold_pct": 65.0,
                "actual_pct": avg_retention,
                "learning_note": "Strong retention — hook + structure patterns worth reusing",
            },
            quality_snapshot={"avg_retention_pct": avg_retention},
            caused_by_event_id=snapshot_event.id if snapshot_event else None,
        )
        events.append(signal)

    return events


def _detect_early_drop(curve: list[dict], second: int = 30) -> bool:
    """Return True if retention drops >20% in the first `second` seconds."""
    if not curve or len(curve) < 2:
        return False
    start = curve[0].get("retention_pct", 100.0)
    for point in curve:
        if point.get("second", 0) >= second:
            at_t = point.get("retention_pct", start)
            return (start - at_t) > 20.0
    return False


def _detect_midpoint_cliff(curve: list[dict]) -> bool:
    """Return True if there's a >15% drop around the 50% mark of the video."""
    if len(curve) < 4:
        return False
    mid_idx = len(curve) // 2
    window = curve[max(0, mid_idx - 1): mid_idx + 2]
    if len(window) < 2:
        return False
    drops = [
        window[i].get("retention_pct", 100) - window[i + 1].get("retention_pct", 100)
        for i in range(len(window) - 1)
    ]
    return any(d > 15.0 for d in drops)


def _annotate_langfuse_low_retention(video_project_id: str, avg_retention: float) -> None:
    """
    Score the Langfuse session for this video project with a low-retention label.
    This feeds the closed-loop: agents can query Langfuse for sessions scored "low".
    """
    try:
        from core.langfuse import get_langfuse_client
        client = get_langfuse_client()
        if client:
            client.score(
                name="youtube_avg_retention",
                value=avg_retention / 100.0,   # Normalize to 0.0-1.0
                comment=f"Actual YouTube avg retention: {avg_retention:.1f}%",
                session_id=video_project_id,
            )
            logger.info(
                "Langfuse retention score submitted",
                video_project_id=video_project_id,
                score=avg_retention,
            )
    except Exception as e:
        logger.warning("Langfuse score submission failed", error=str(e))
