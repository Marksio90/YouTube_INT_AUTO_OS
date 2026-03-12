"""Tests for health and root endpoints."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["agents"] == 23
    assert data["layers"] == 5


async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "YouTube" in data["message"]
    assert data["docs"] == "/docs"
