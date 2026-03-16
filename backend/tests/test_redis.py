"""Tests for Redis integration: token blacklist and logout endpoint."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRedisHealthCheck:
    async def test_health_includes_redis_status(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "redis" in data
        assert data["redis"] == "ok"


class TestTokenBlacklist:
    async def test_blacklisted_token_is_rejected(self, client: AsyncClient, test_user, auth_headers):
        # Token works before logout
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200

        # Logout — revokes the token
        resp = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert resp.status_code == 204

        # Same token is now rejected
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 401
        assert "revoked" in resp.json()["detail"].lower()

    async def test_logout_requires_authentication(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 401

    async def test_new_token_works_after_logout(self, client: AsyncClient, test_user, auth_headers):
        # Logout old token
        await client.post("/api/v1/auth/logout", headers=auth_headers)

        # Re-login to obtain a fresh token
        resp = await client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert resp.status_code == 200
        new_token = resp.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}

        # New token is valid
        resp = await client.get("/api/v1/auth/me", headers=new_headers)
        assert resp.status_code == 200
