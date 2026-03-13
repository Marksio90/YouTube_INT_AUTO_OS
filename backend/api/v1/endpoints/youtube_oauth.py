"""
YouTube OAuth 2.0 Endpoints
Handles the Google OAuth flow for connecting YouTube channels.

Flow:
  1. GET /youtube-oauth/{channel_id}/authorize  → redirect URL for user
  2. GET /youtube-oauth/callback                → Google redirects here with ?code=
  3. GET /youtube-oauth/{channel_id}/status     → check if channel is authorized
  4. DELETE /youtube-oauth/{channel_id}/revoke  → disconnect channel
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from urllib.parse import urlparse

from services.youtube_oauth_service import youtube_oauth_service
from core.config import settings
from core.auth import get_current_user
from models.user import User

router = APIRouter(prefix="/youtube-oauth", tags=["YouTube OAuth"])

# Redirect URI must match what's registered in Google Cloud Console
_REDIRECT_URI_PATH = "/api/v1/youtube-oauth/callback"


def _validate_base_url(base_url: str) -> str:
    """Validate that base_url is in the allowed origins whitelist."""
    normalized = base_url.rstrip("/")
    allowed = [o.rstrip("/") for o in settings.allowed_origins]
    if normalized not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"base_url '{base_url}' is not in the allowed origins list. "
                   f"Configure ALLOWED_ORIGINS to include this URL.",
        )
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="base_url must use http or https scheme")
    return normalized


def _build_redirect_uri(request_base_url: str) -> str:
    base = _validate_base_url(request_base_url)
    return f"{base}{_REDIRECT_URI_PATH}"


@router.get("/{channel_id}/authorize")
async def start_oauth(
    channel_id: str,
    base_url: str = Query(..., description="Base URL of this server — must be in ALLOWED_ORIGINS"),
    current_user: User = Depends(get_current_user),
):
    """
    Generate Google OAuth authorization URL for a channel.
    Redirect the user to the returned URL to grant access.
    """
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        raise HTTPException(
            status_code=503,
            detail="YouTube OAuth not configured. Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET.",
        )
    redirect_uri = _build_redirect_uri(base_url)
    url = youtube_oauth_service.get_authorization_url(
        redirect_uri=redirect_uri,
        state=channel_id,  # pass channel_id through state param
    )
    return {"authorization_url": url, "channel_id": channel_id}


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(..., description="channel_id passed as state"),
    base_url: str = Query(..., description="Base URL used when starting OAuth — must be in ALLOWED_ORIGINS"),
):
    """
    Google redirects here after user grants/denies access.
    Exchanges authorization code for tokens and stores them for the channel.
    Note: No auth required — this endpoint is called by Google's OAuth servers.
    """
    channel_id = state
    redirect_uri = _build_redirect_uri(base_url)

    try:
        tokens = await youtube_oauth_service.exchange_code(code, redirect_uri)
        await youtube_oauth_service.save_tokens_for_channel(channel_id, tokens)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth token exchange failed: {str(e)}")

    return {
        "success": True,
        "channel_id": channel_id,
        "message": "YouTube channel authorized successfully.",
        "has_refresh_token": bool(tokens.get("refresh_token")),
    }


@router.get("/{channel_id}/status")
async def oauth_status(
    channel_id: str,
    current_user: User = Depends(get_current_user),
):
    """Check YouTube OAuth authorization status for a channel."""
    status = await youtube_oauth_service.get_token_status(channel_id)
    return {"channel_id": channel_id, **status}


@router.delete("/{channel_id}/revoke")
async def oauth_revoke(
    channel_id: str,
    current_user: User = Depends(get_current_user),
):
    """Revoke stored YouTube OAuth tokens for a channel."""
    try:
        await youtube_oauth_service.revoke_tokens(channel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "channel_id": channel_id, "message": "YouTube OAuth tokens revoked."}
