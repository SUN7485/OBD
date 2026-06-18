import pytest
from httpx import AsyncClient
from ..main import app
from ..config.settings import settings

LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
HEALTH_URL = "/api/v1/health/"

@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient):
    res = await test_client.post(
        LOGIN_URL,
        json={"email": "admin@test.com", "password": "admin123"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data and "refresh_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(test_client: AsyncClient):
    res = await test_client.post(
        LOGIN_URL,
        json={"email": "admin@test.com", "password": "wrongpass"}
    )
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_jwt_token_validity_and_refresh(test_client: AsyncClient):
    login_res = await test_client.post(
        LOGIN_URL,
        json={"email": "admin@test.com", "password": "admin123"}
    )
    tokens = login_res.json()
    # Test refresh flow
    refresh_res = await test_client.post(
        REFRESH_URL,
        json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    # Test protected endpoint with new access token
    headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    health_res = await test_client.get(HEALTH_URL, headers=headers)
    assert health_res.status_code in (200, 503)  # Service might be unhealthy if DB/Redis mock

@pytest.mark.asyncio
async def test_protected_endpoint_requires_token(test_client: AsyncClient):
    res = await test_client.post(LOGOUT_URL)
    assert res.status_code == 401 or res.status_code == 403

@pytest.mark.asyncio
async def test_logout_endpoint(test_client: AsyncClient):
    login_res = await test_client.post(
        LOGIN_URL,
        json={"email": "admin@test.com", "password": "admin123"}
    )
    tokens = login_res.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    logout_res = await test_client.post(LOGOUT_URL, headers=headers)
    assert logout_res.status_code == 200
    assert "detail" in logout_res.json()

# RBAC test stubs (require more endpoint setup for meaningful checks)