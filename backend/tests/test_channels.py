"""Tests for channel CRUD endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestChannelCRUD:
    async def test_create_channel(self, client: AsyncClient):
        resp = await client.post("/api/v1/channels", json={
            "name": "Test Finance Channel",
            "niche": "personal_finance",
            "description": "Financial education channel",
            "content_pillars": ["investing", "budgeting"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Finance Channel"
        assert data["niche"] == "personal_finance"
        assert "id" in data
        return data["id"]

    async def test_list_channels(self, client: AsyncClient):
        # Create a channel first
        await client.post("/api/v1/channels", json={
            "name": "List Test Channel",
            "niche": "tech",
        })
        resp = await client.get("/api/v1/channels")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_get_channel(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/channels", json={
            "name": "Get Test Channel",
            "niche": "gaming",
        })
        channel_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/channels/{channel_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == channel_id

    async def test_get_channel_not_found(self, client: AsyncClient):
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.get(f"/api/v1/channels/{fake_id}")
        assert resp.status_code == 404

    async def test_update_channel(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/channels", json={
            "name": "Update Test Channel",
            "niche": "fitness",
        })
        channel_id = create_resp.json()["id"]

        resp = await client.patch(f"/api/v1/channels/{channel_id}", json={
            "description": "Updated description",
        })
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    async def test_delete_channel_soft_delete(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/channels", json={
            "name": "Delete Test Channel",
            "niche": "cooking",
        })
        channel_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/channels/{channel_id}")
        assert resp.status_code == 204

    async def test_list_channels_filter_active(self, client: AsyncClient):
        resp = await client.get("/api/v1/channels?is_active=true")
        assert resp.status_code == 200
