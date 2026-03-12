"""Tests for video project endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def channel_id(client: AsyncClient) -> str:
    """Create a channel and return its ID for video tests."""
    resp = await client.post("/api/v1/channels", json={
        "name": "Video Test Channel",
        "niche": "education",
    })
    return resp.json()["id"]


class TestVideoCRUD:
    async def test_create_video(self, client: AsyncClient, channel_id: str):
        resp = await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "How to Invest in 2026 — Complete Guide",
            "format": "long_form",
            "niche": "personal_finance",
            "target_keywords": ["investing", "2026", "beginner"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "How to Invest in 2026 — Complete Guide"
        assert data["stage"] == "idea"
        assert data["format"] == "long_form"

    async def test_create_video_short_title_rejected(self, client: AsyncClient, channel_id: str):
        resp = await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "Hi",
        })
        assert resp.status_code == 422

    async def test_list_videos(self, client: AsyncClient, channel_id: str):
        await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "List Test Video Title Here",
        })
        resp = await client.get("/api/v1/videos")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_videos_filter_by_channel(self, client: AsyncClient, channel_id: str):
        await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "Filtered Video Title Example",
        })
        resp = await client.get(f"/api/v1/videos?channel_id={channel_id}")
        assert resp.status_code == 200
        videos = resp.json()
        for v in videos:
            assert v["channel_id"] == channel_id

    async def test_get_video(self, client: AsyncClient, channel_id: str):
        create_resp = await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "Get Video Test Title Here",
        })
        video_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/videos/{video_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == video_id

    async def test_get_video_not_found(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/api/v1/videos/{fake_id}")
        assert resp.status_code == 404

    async def test_update_video_stage(self, client: AsyncClient, channel_id: str):
        create_resp = await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "Stage Advance Test Title",
        })
        video_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/v1/videos/{video_id}", json={
            "stage": "script",
        })
        assert resp.status_code == 200
        assert resp.json()["stage"] == "script"

    async def test_update_video_invalid_stage(self, client: AsyncClient, channel_id: str):
        create_resp = await client.post("/api/v1/videos", json={
            "channel_id": channel_id,
            "title": "Invalid Stage Test Title",
        })
        video_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/v1/videos/{video_id}", json={
            "stage": "nonexistent_stage",
        })
        assert resp.status_code == 400
