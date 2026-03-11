"""
YouTube OAuth 2.0 Service
Handles Google OAuth flow for YouTube Data API access:
- Authorization URL generation
- Token exchange (code → access + refresh tokens)
- Token refresh (automatic when expired)
- Persistent token storage per channel (in Channel.blueprint['_oauth'])

Scopes used:
  - youtube.upload   → video uploads
  - youtube.readonly → channel analytics
  - yt-analytics.readonly → retention data
"""
import time
from typing import Optional, Dict
from urllib.parse import urlencode
import httpx
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


class YouTubeOAuthService:
    def __init__(self):
        self.client_id = settings.youtube_client_id
        self.client_secret = settings.youtube_client_secret

    def _is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, redirect_uri: str, state: str = "") -> str:
        """
        Generate Google OAuth 2.0 authorization URL.
        User visits this URL, grants access, is redirected with ?code=...
        """
        if not self._is_configured():
            raise ValueError("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are not configured")

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",   # offline = get refresh_token
            "prompt": "consent",         # force consent to always get refresh_token
        }
        if state:
            params["state"] = state

        return f"{GOOGLE_AUTH_BASE}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict:
        """
        Exchange authorization code for access + refresh tokens.
        Returns token dict with: access_token, refresh_token, expires_at.
        """
        if not self._is_configured():
            raise ValueError("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", ""),
            "expires_at": int(time.time()) + int(data.get("expires_in", 3600)),
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope", ""),
        }
        logger.info("YouTube OAuth tokens obtained", has_refresh=bool(tokens["refresh_token"]))
        return tokens

    async def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Use refresh_token to get a new access_token.
        Returns updated token dict.
        """
        if not self._is_configured():
            raise ValueError("YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET are not configured")

        if not refresh_token:
            raise ValueError("No refresh_token provided — user must re-authorize")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        tokens = {
            "access_token": data["access_token"],
            "refresh_token": refresh_token,  # refresh_token doesn't change
            "expires_at": int(time.time()) + int(data.get("expires_in", 3600)),
            "token_type": data.get("token_type", "Bearer"),
        }
        logger.info("YouTube access token refreshed")
        return tokens

    async def get_valid_access_token(self, channel_id: str) -> Optional[str]:
        """
        Get a valid (non-expired) access token for a channel.
        Auto-refreshes if expired. Returns None if channel not authorized.
        """
        tokens = await self._load_tokens(channel_id)
        if not tokens:
            logger.warning("Channel not authorized with YouTube OAuth", channel_id=channel_id)
            return None

        # Refresh if expires in < 5 minutes
        if time.time() > tokens["expires_at"] - 300:
            if not tokens.get("refresh_token"):
                logger.warning("Token expired, no refresh_token", channel_id=channel_id)
                return None
            try:
                tokens = await self.refresh_access_token(tokens["refresh_token"])
                await self._save_tokens(channel_id, tokens)
            except Exception as e:
                logger.error("Token refresh failed", channel_id=channel_id, error=str(e))
                return None

        return tokens["access_token"]

    async def save_tokens_for_channel(self, channel_id: str, tokens: Dict) -> None:
        """Persist OAuth tokens for a channel in DB (Channel.blueprint['_oauth'])."""
        await self._save_tokens(channel_id, tokens)

    async def revoke_tokens(self, channel_id: str) -> None:
        """Remove stored OAuth tokens for a channel."""
        await self._save_tokens(channel_id, None)
        logger.info("YouTube OAuth tokens revoked", channel_id=channel_id)

    async def get_token_status(self, channel_id: str) -> Dict:
        """Return OAuth status for a channel (without exposing tokens)."""
        tokens = await self._load_tokens(channel_id)
        if not tokens:
            return {"authorized": False}
        is_expired = time.time() > tokens["expires_at"] - 300
        return {
            "authorized": True,
            "has_refresh_token": bool(tokens.get("refresh_token")),
            "expires_at": tokens["expires_at"],
            "is_expired": is_expired,
            "can_auto_refresh": bool(tokens.get("refresh_token")),
        }

    # ------------------------------------------------------------------
    # Internal: store tokens in Channel.blueprint["_oauth"]
    # ------------------------------------------------------------------

    async def _load_tokens(self, channel_id: str) -> Optional[Dict]:
        from core.database import AsyncSessionLocal
        from models.channel import Channel
        from sqlalchemy import select
        from uuid import UUID

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Channel).where(Channel.id == UUID(channel_id))
            )
            channel = result.scalar_one_or_none()
            if not channel:
                return None
            blueprint = channel.blueprint or {}
            return blueprint.get("_oauth")

    async def _save_tokens(self, channel_id: str, tokens: Optional[Dict]) -> None:
        from core.database import AsyncSessionLocal
        from models.channel import Channel
        from sqlalchemy import select
        from uuid import UUID

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Channel).where(Channel.id == UUID(channel_id))
            )
            channel = result.scalar_one_or_none()
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")

            blueprint = dict(channel.blueprint or {})
            if tokens is None:
                blueprint.pop("_oauth", None)
            else:
                blueprint["_oauth"] = tokens
            channel.blueprint = blueprint
            await db.commit()


youtube_oauth_service = YouTubeOAuthService()
