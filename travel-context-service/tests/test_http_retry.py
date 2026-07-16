import httpx
import pytest

from app.services.http_retry import request_with_retry


@pytest.mark.asyncio
async def test_request_with_retry_recovers_from_transient_status():
    responses = [
        httpx.Response(503, request=httpx.Request("GET", "https://example.test")),
        httpx.Response(200, request=httpx.Request("GET", "https://example.test")),
    ]

    async def request():
        return responses.pop(0)

    response = await request_with_retry(request, base_delay_seconds=0)

    assert response.status_code == 200
    assert responses == []


@pytest.mark.asyncio
async def test_request_with_retry_stops_after_bound():
    calls = 0

    async def request():
        nonlocal calls
        calls += 1
        raise httpx.TimeoutException("timed out")

    with pytest.raises(httpx.TimeoutException):
        await request_with_retry(request, attempts=2, base_delay_seconds=0)

    assert calls == 2
