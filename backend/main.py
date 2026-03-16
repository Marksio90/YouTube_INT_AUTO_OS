from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog
import asyncio
import json

from core.config import settings
from core.database import init_db, close_db
from core.langfuse import flush as langfuse_flush, is_enabled as langfuse_enabled
from core.redis import init_redis, close_redis, redis_health_check
from api.v1.router import api_router
from core.rate_limit import limiter


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting YouTube Intelligence & Automation OS API",
        env=settings.app_env,
        langfuse_enabled=langfuse_enabled(),
    )
    await init_db()
    await init_redis()
    yield
    langfuse_flush()
    await close_db()
    await close_redis()
    logger.info("API shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    ## YouTube Intelligence & Automation OS

    AI-Native Operating System do Budowy i Skalowania Oryginalnych,
    Zgodnych z Politykami, Wysoko-Konwertujacych Marek Contentowych na YouTube.

    ### 5 Warstw Platformy:
    - **Layer 1**: Market Intelligence (Niche Hunter, Opportunity Mapper, Competitive Deconstruction)
    - **Layer 2**: Content Design Engine (Channel Architect, Script Strategist, Voice Persona)
    - **Layer 3**: AI Production Engine (Hook Specialist, Thumbnail Psychology, Video Assembly, ...)
    - **Layer 4**: Optimization & Experimentation (SEO Intelligence, Experimentation, Watch-Time Forensics)
    - **Layer 5**: Compliance & Monetization (Originality & Transformation, Rights & Risk, Monetization Readiness)

    ### Quality Gates:
    - Niche Score ≥ 70/100
    - Hook Score ≥ 8/10
    - Originality Score ≥ 85/100
    - SEO Score ≥ 75/100
    - Similarity cosine < 0.85
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting — attach state and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/health")
async def health_check():
    redis_ok = await redis_health_check()
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "agents": 23,
        "layers": 5,
        "redis": "ok" if redis_ok else "unavailable",
    }


@app.get("/")
async def root():
    return {
        "message": "YouTube Intelligence & Automation OS API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# ============================================================
# Server-Sent Events — real-time agent run status
# ============================================================

@app.get("/api/v1/agents/runs/{run_id}/stream")
async def stream_agent_run(run_id: str, request: Request):
    """
    SSE endpoint for real-time agent run status updates.
    Frontend polls this to get live progress without websockets.
    """
    from sqlalchemy import select
    from core.database import AsyncSessionLocal
    from models.agent import AgentRun, AgentStatus
    from uuid import UUID

    async def event_generator():
        last_status = None
        max_polls = 300  # 5 minutes max at 1s intervals

        for _ in range(max_polls):
            if await request.is_disconnected():
                break

            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(AgentRun).where(AgentRun.id == UUID(run_id))
                    )
                    run = result.scalar_one_or_none()

                if not run:
                    yield f"data: {json.dumps({'error': 'Run not found'})}\n\n"
                    break

                current_status = run.status.value if run.status else "unknown"
                if current_status != last_status:
                    payload = {
                        "run_id": run_id,
                        "status": current_status,
                        "agent_id": run.agent_id,
                        "output_data": run.output_data,
                        "error_message": run.error_message,
                        "duration_seconds": run.duration_seconds,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    last_status = current_status

                if current_status in ("completed", "error", "cancelled"):
                    break

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break

            await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
