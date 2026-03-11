from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from core.config import settings
from core.database import init_db, close_db
from api.v1.router import api_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting YouTube Intelligence & Automation OS API", env=settings.app_env)
    await init_db()
    yield
    await close_db()
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
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "agents": 23,
        "layers": 5,
    }


@app.get("/")
async def root():
    return {
        "message": "YouTube Intelligence & Automation OS API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
