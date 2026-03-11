from fastapi import APIRouter
from api.v1.endpoints import auth, channels, videos, agents, scripts, dashboard
from api.v1.endpoints import youtube_oauth

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(channels.router)
api_router.include_router(videos.router)
api_router.include_router(agents.router)
api_router.include_router(scripts.router)
api_router.include_router(dashboard.router)
api_router.include_router(youtube_oauth.router)
