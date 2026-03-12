"""
YouTube Data API v3 Integration
Handles: channel metrics, video analytics, search, publishing.

Quota: 10,000 units/day default
- Upload: 1,600 units → ~6 uploads/day
- Search: 100 units per request
- Channels/Videos read: 1 unit
- Analytics read: 1 unit

Rate limiting is handled automatically with exponential backoff.
"""
import asyncio
import re
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any
import httpx
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"

# Quota costs per operation type (YouTube Data API v3)
_QUOTA_COSTS = {
    "search": 100,
    "channels": 1,
    "videos": 1,
    "upload": 1600,
    "analytics": 1,
    "default": 1,
}


class YouTubeService:
    def __init__(self):
        self.api_key = settings.youtube_api_key
        self._quota_used_today = 0
        self._quota_reset_date = date.today()

    # ============================================================
    # Channel Metrics
    # ============================================================

    async def get_channel_stats(self, youtube_channel_id: str) -> Optional[Dict]:
        """Fetch channel statistics from YouTube Data API."""
        if not self.api_key:
            logger.warning("YouTube API key not configured")
            return None

        async with httpx.AsyncClient() as client:
            response = await self._api_call(
                client,
                f"{YOUTUBE_API_BASE}/channels",
                params={
                    "part": "snippet,statistics,brandingSettings",
                    "id": youtube_channel_id,
                    "key": self.api_key,
                },
            )

        items = response.get("items", [])
        if not items:
            return None

        item = items[0]
        stats = item.get("statistics", {})
        return {
            "youtube_channel_id": youtube_channel_id,
            "title": item.get("snippet", {}).get("title"),
            "description": item.get("snippet", {}).get("description"),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "thumbnail_url": item.get("snippet", {}).get("thumbnails", {}).get("high", {}).get("url"),
        }

    async def sync_channel_metrics(self, channel_id: str, youtube_channel_id: str):
        """Fetch YouTube stats and update channel in DB."""
        from core.database import AsyncSessionLocal
        from models.channel import Channel
        from sqlalchemy import select
        from uuid import UUID

        stats = await self.get_channel_stats(youtube_channel_id)
        if not stats:
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Channel).where(Channel.id == UUID(channel_id)))
            channel = result.scalar_one_or_none()
            if channel:
                channel.subscribers = stats["subscribers"]
                channel.total_views = stats["total_views"]
                await db.commit()
                logger.info("Channel metrics synced", channel_id=channel_id, subscribers=stats["subscribers"])

    # ============================================================
    # Video Search (SEO Intelligence input)
    # ============================================================

    async def search_videos(
        self,
        query: str,
        max_results: int = 25,
        order: str = "relevance",
        published_after: Optional[str] = None,
    ) -> List[Dict]:
        """Search YouTube videos. Used by SEO Intelligence Agent."""
        if not self.api_key:
            return []

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
            "key": self.api_key,
        }
        if published_after:
            params["publishedAfter"] = published_after

        async with httpx.AsyncClient() as client:
            response = await self._api_call(client, f"{YOUTUBE_API_BASE}/search", params=params)

        return [
            {
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"][:200],
                "channel_title": item["snippet"]["channelTitle"],
                "published_at": item["snippet"]["publishedAt"],
                "thumbnail_url": item["snippet"]["thumbnails"]["medium"]["url"],
            }
            for item in response.get("items", [])
        ]

    async def get_video_stats(self, video_ids: List[str]) -> List[Dict]:
        """Get statistics for multiple videos (up to 50)."""
        if not self.api_key or not video_ids:
            return []

        ids_str = ",".join(video_ids[:50])
        async with httpx.AsyncClient() as client:
            response = await self._api_call(
                client,
                f"{YOUTUBE_API_BASE}/videos",
                params={
                    "part": "statistics,contentDetails",
                    "id": ids_str,
                    "key": self.api_key,
                },
            )

        return [
            {
                "video_id": item["id"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "comments": int(item["statistics"].get("commentCount", 0)),
                "duration": item["contentDetails"].get("duration"),  # ISO 8601
            }
            for item in response.get("items", [])
        ]

    # ============================================================
    # Video Upload
    # ============================================================

    async def get_upload_token(self, access_token: str, video_metadata: Dict) -> str:
        """
        Get resumable upload URL from YouTube.
        Costs 1,600 quota units.
        Returns upload URL for subsequent PUT request.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": "video/mp4",
        }
        body = {
            "snippet": {
                "title": video_metadata["title"],
                "description": video_metadata.get("description", ""),
                "tags": video_metadata.get("tags", []),
                "categoryId": video_metadata.get("category_id", "22"),  # 22 = People & Blogs
                "defaultLanguage": video_metadata.get("language", "pl"),
            },
            "status": {
                "privacyStatus": video_metadata.get("privacy_status", "private"),
                "selfDeclaredMadeForKids": False,
                "containsSyntheticMedia": video_metadata.get("contains_ai_content", False),
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{YOUTUBE_API_BASE}/videos?uploadType=resumable&part=snippet,status",
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            return response.headers.get("Location", "")

    # ============================================================
    # Analytics (OAuth required)
    # ============================================================

    async def get_video_retention(
        self, video_id: str, access_token: str
    ) -> List[Dict]:
        """
        Get audience retention data for a video.
        Returns list of {elapsed_video_time_ratio, audience_watch_ratio} points.
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "ids": "channel==MINE",
            "metrics": "audienceWatchRatio,relativeRetentionPerformance",
            "dimensions": "elapsedVideoTimeRatio",
            "filters": f"video=={video_id}",
            "startDate": "2020-01-01",
            "endDate": date.today().isoformat(),
        }

        async with httpx.AsyncClient() as client:
            response = await self._api_call(
                client, f"{YOUTUBE_ANALYTICS_BASE}/reports",
                params=params, headers=headers,
            )

        rows = response.get("rows", [])
        return [
            {
                "elapsed_ratio": row[0],
                "audience_ratio": row[1],
                "relative_performance": row[2] if len(row) > 2 else None,
            }
            for row in rows
        ]

    async def get_channel_analytics(
        self, access_token: str, start_date: str, end_date: str
    ) -> Dict:
        """Get channel-level analytics (views, watch time, revenue, CTR)."""
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            "ids": "channel==MINE",
            "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,estimatedRevenue,ctr",
            "startDate": start_date,
            "endDate": end_date,
        }

        async with httpx.AsyncClient() as client:
            return await self._api_call(
                client, f"{YOUTUBE_ANALYTICS_BASE}/reports",
                params=params, headers=headers,
            )

    async def upload_video(
        self,
        channel_id: str,
        video_path: str,
        video_metadata: Dict,
    ) -> Optional[str]:
        """
        Upload video to YouTube using stored OAuth token for the channel.
        Returns YouTube video URL or None if upload fails.
        Costs ~1600 quota units.
        """
        from services.youtube_oauth_service import youtube_oauth_service

        access_token = await youtube_oauth_service.get_valid_access_token(channel_id)
        if not access_token:
            logger.error("Cannot upload: channel not authorized with YouTube OAuth", channel_id=channel_id)
            return None

        # Step 1: Get resumable upload URL
        upload_url = await self.get_upload_token(access_token, video_metadata)
        if not upload_url:
            logger.error("Failed to get upload URL from YouTube", channel_id=channel_id)
            return None

        # Step 2: Upload video file via PUT
        async with httpx.AsyncClient(timeout=600.0) as client:
            with open(video_path, "rb") as f:
                video_bytes = f.read()
            response = await client.put(
                upload_url,
                content=video_bytes,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(video_bytes)),
                },
            )
            response.raise_for_status()
            data = response.json()

        video_id = data.get("id")
        if not video_id:
            logger.error("Upload succeeded but no video ID returned", channel_id=channel_id)
            return None

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info("Video uploaded to YouTube", channel_id=channel_id, video_id=video_id, url=video_url)
        return video_url

    async def sync_video_analytics(self, video_project_id: str, published_url: str, channel_id: str = None):
        """Sync YouTube Analytics to VideoAnalytics model in DB."""
        from services.youtube_oauth_service import youtube_oauth_service

        video_id = self._extract_video_id(published_url)
        if not video_id:
            return

        if not channel_id:
            logger.info("Video analytics sync skipped — channel_id not provided", video_id=video_id)
            return

        access_token = await youtube_oauth_service.get_valid_access_token(channel_id)
        if not access_token:
            logger.warning("Cannot sync analytics: channel not authorized", channel_id=channel_id)
            return

        retention_data = await self.get_video_retention(video_id, access_token)
        logger.info(
            "Video analytics synced",
            video_id=video_id,
            project_id=video_project_id,
            retention_points=len(retention_data),
        )

    # ============================================================
    # Trending / Research
    # ============================================================

    async def get_trending_videos(self, region_code: str = "PL", category_id: str = "") -> List[Dict]:
        """Get trending videos for niche research."""
        if not self.api_key:
            return []

        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": 50,
            "key": self.api_key,
        }
        if category_id:
            params["videoCategoryId"] = category_id

        async with httpx.AsyncClient() as client:
            response = await self._api_call(client, f"{YOUTUBE_API_BASE}/videos", params=params)

        return [
            {
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "published_at": item["snippet"]["publishedAt"],
            }
            for item in response.get("items", [])
        ]

    async def get_keyword_suggestions(self, seed_keyword: str, language: str = "pl") -> List[str]:
        """
        Get keyword suggestions via YouTube autocomplete.
        Not in official API — uses undocumented suggest endpoint.
        """
        import json as _json
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://suggestqueries.google.com/complete/search",
                    params={
                        "client": "youtube",
                        "ds": "yt",
                        "q": seed_keyword,
                        "hl": language,
                    },
                    timeout=5.0,
                )
                if response.status_code == 200:
                    # Response format: [query, [[suggestion, 0, [], {}], ...]]
                    raw = response.text.strip()
                    # Validate expected JSONP-like format before parsing
                    if not raw.startswith("(") and not raw.startswith("window."):
                        # Try direct JSON parse (some endpoints return plain JSON)
                        data = _json.loads(raw)
                    else:
                        inner = raw.split("(", 1)[-1].rstrip(")")
                        data = _json.loads(inner)
                    suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
                    return [item[0] for item in suggestions[:10] if isinstance(item, list) and item]
            except Exception as e:
                logger.warning("Keyword suggestions failed", error=str(e))
        return []

    # ============================================================
    # Helpers
    # ============================================================

    def _charge_quota(self, url: str) -> int:
        """Determine quota cost from URL and increment counter. Resets at midnight."""
        today = date.today()
        if today != self._quota_reset_date:
            self._quota_used_today = 0
            self._quota_reset_date = today

        # Derive operation type from URL path
        for key in _QUOTA_COSTS:
            if f"/{key}" in url:
                cost = _QUOTA_COSTS[key]
                break
        else:
            cost = _QUOTA_COSTS["default"]

        self._quota_used_today += cost
        logger.debug("YouTube quota charged", cost=cost, total_used=self._quota_used_today, url=url)
        return cost

    async def _api_call(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict = None,
        headers: dict = None,
        retries: int = 3,
    ) -> Dict:
        if self.quota_remaining <= 0:
            raise Exception("YouTube API daily quota exhausted. Try again tomorrow.")

        for attempt in range(retries):
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                if response.status_code == 200:
                    self._charge_quota(url)
                    return response.json()
                elif response.status_code == 429:
                    wait = 2 ** attempt * 2
                    logger.warning("YouTube API rate limit", wait_seconds=wait)
                    await asyncio.sleep(wait)
                elif response.status_code == 403:
                    error = response.json().get("error", {})
                    if "quotaExceeded" in str(error):
                        self._quota_used_today = settings.youtube_daily_api_quota  # mark as exhausted
                        raise Exception("YouTube API daily quota exceeded (10,000 units)")
                    raise Exception(f"YouTube API forbidden: {error}")
                else:
                    raise Exception(f"YouTube API error {response.status_code}: {response.text[:200]}")
            except httpx.TimeoutException:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return {}

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
            r"(?:embed/)([a-zA-Z0-9_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @property
    def quota_remaining(self) -> int:
        today = date.today()
        if today != self._quota_reset_date:
            self._quota_used_today = 0
            self._quota_reset_date = today
        return settings.youtube_daily_api_quota - self._quota_used_today


youtube_service = YouTubeService()
