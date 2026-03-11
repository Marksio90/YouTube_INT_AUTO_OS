"""
YouTube Data API v3 Integration
Handles: channel metrics, video analytics, search, publishing.

Quota: 10,000 units/day default
- Upload: 1,600 units → ~6 uploads/day
- Search: 100 units per request
- Analytics read: 1 unit

Rate limiting is handled automatically with exponential backoff.
"""
import asyncio
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any
import httpx
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"


class YouTubeService:
    def __init__(self):
        self.api_key = settings.youtube_api_key
        self._quota_used_today = 0

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

    async def sync_video_analytics(self, video_project_id: str, published_url: str):
        """Sync YouTube Analytics to VideoAnalytics model in DB."""
        # In production: extract video_id from URL, use OAuth token, fetch metrics
        video_id = self._extract_video_id(published_url)
        if not video_id:
            return

        # TODO: Use stored OAuth token for the channel
        logger.info("Video analytics sync queued", video_id=video_id, project_id=video_project_id)

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
                    import json
                    data = json.loads(response.text.split("(", 1)[1].rstrip(")"))
                    return [item[0] for item in data[1][:10]]
            except Exception as e:
                logger.warning("Keyword suggestions failed", error=str(e))
        return []

    # ============================================================
    # Helpers
    # ============================================================

    async def _api_call(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict = None,
        headers: dict = None,
        retries: int = 3,
    ) -> Dict:
        for attempt in range(retries):
            try:
                response = await client.get(url, params=params, headers=headers, timeout=30.0)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    wait = 2 ** attempt * 2
                    logger.warning("YouTube API rate limit", wait_seconds=wait)
                    await asyncio.sleep(wait)
                elif response.status_code == 403:
                    error = response.json().get("error", {})
                    if "quotaExceeded" in str(error):
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
        import re
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
        return settings.youtube_daily_api_quota - self._quota_used_today


youtube_service = YouTubeService()
