import asyncio
from collections.abc import Awaitable, Callable

import httpx

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def request_with_retry(
    request: Callable[[], Awaitable[httpx.Response]],
    attempts: int = 3,
    base_delay_seconds: float = 0.1,
) -> httpx.Response:
    """Retry bounded transient HTTP failures and return the final response."""
    if attempts < 1:
        raise ValueError("attempts must be positive")

    for attempt in range(attempts):
        try:
            response = await request()
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == attempts - 1:
                raise
        else:
            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            if attempt == attempts - 1:
                return response

        await asyncio.sleep(base_delay_seconds * (2**attempt))

    raise RuntimeError("retry loop exited unexpectedly")
