import httpx
import pytest

from app.models.schemas import GenerationPreferences
from app.services.travel_context_client import TravelContextClient


class FakeResponse:
    def __init__(self, payload, status_error=None):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.payload


class FakeAsyncClient:
    instances = []
    next_response = None
    next_error = None

    def __init__(self, timeout):
        self.timeout = timeout
        self.post_url = None
        self.post_payload = None
        FakeAsyncClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, json):
        self.post_url = url
        self.post_payload = json
        if FakeAsyncClient.next_error:
            raise FakeAsyncClient.next_error
        return FakeAsyncClient.next_response


@pytest.fixture(autouse=True)
def reset_fake_client():
    FakeAsyncClient.instances = []
    FakeAsyncClient.next_response = None
    FakeAsyncClient.next_error = None


def preferences():
    return GenerationPreferences(
        destination="Munich",
        startDate="2026-06-01",
        endDate="2026-06-03",
        vibe="cultural",
    )


@pytest.mark.asyncio
async def test_travel_context_client_returns_none_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.services.travel_context_client.httpx.AsyncClient", FakeAsyncClient
    )
    client = TravelContextClient(base_url="http://context-service", enabled=False)

    context = await client.get_trip_context(preferences())

    assert context is None
    assert FakeAsyncClient.instances == []


@pytest.mark.asyncio
async def test_travel_context_client_posts_preferences_and_maps_context(monkeypatch):
    monkeypatch.setattr(
        "app.services.travel_context_client.httpx.AsyncClient", FakeAsyncClient
    )
    FakeAsyncClient.next_response = FakeResponse(
        {
            "destination": "Munich",
            "coordinates": {"lat": 48.137154, "lon": 11.576124},
            "events": [
                {
                    "source": "serpapi_google_events",
                    "sourceId": "event-1",
                    "title": "Summer Festival",
                    "venueName": "Olympiapark",
                    "score": 42,
                }
            ],
            "places": [],
            "weather": [],
        }
    )
    client = TravelContextClient(
        base_url="http://context-service/",
        timeout_seconds=2.5,
        enabled=True,
    )

    context = await client.get_trip_context(preferences(), include_events=False)

    fake_client = FakeAsyncClient.instances[0]
    assert fake_client.timeout == 2.5
    assert fake_client.post_url == "http://context-service/trip-context"
    assert fake_client.post_payload == {
        "destination": "Munich",
        "startDate": "2026-06-01",
        "endDate": "2026-06-03",
        "vibe": "cultural",
        "includeEvents": False,
    }
    assert context is not None
    assert context.destination == "Munich"
    assert context.coordinates.lat == 48.137154
    assert context.events[0].title == "Summer Festival"


@pytest.mark.asyncio
async def test_travel_context_client_returns_none_when_downstream_fails(monkeypatch):
    monkeypatch.setattr(
        "app.services.travel_context_client.httpx.AsyncClient", FakeAsyncClient
    )
    request = httpx.Request("POST", "http://context-service/trip-context")
    response = httpx.Response(503, request=request)
    FakeAsyncClient.next_response = FakeResponse(
        {},
        status_error=httpx.HTTPStatusError(
            "service unavailable",
            request=request,
            response=response,
        ),
    )
    client = TravelContextClient(base_url="http://context-service", enabled=True)

    context = await client.get_trip_context(preferences())

    assert context is None
