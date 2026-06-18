import pytest
from httpx import AsyncClient

HEALTH_URL = "/api/v1/health/"

@pytest.mark.asyncio
async def test_health_api_ok(test_client: AsyncClient):
    res = await test_client.get(HEALTH_URL)
    # Since health depends on actual DB/Redis, 200 = healthy, 503 = degraded/unhealthy (either are valid)
    assert res.status_code in (200, 503)
    data = res.json()
    assert "status" in data and "database" in data and "redis" in data and "lm_studio" in data
    assert data["status"] in ("healthy", "degraded", "unhealthy")

@pytest.mark.asyncio
async def test_health_schema(test_client: AsyncClient):
    res = await test_client.get(HEALTH_URL)
    data = res.json()
    assert isinstance(data["status"], str)
    assert isinstance(data["database"], str)
    assert isinstance(data["redis"], str)
    assert isinstance(data["lm_studio"], str)