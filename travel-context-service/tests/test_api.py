from fastapi.testclient import TestClient

from app.api.routes.context import get_travel_context_service
from app.main import app
from app.models.schemas import Coordinates, EventCandidate, TripContextResponse


class FakeTravelContextService:
    async def build_trip_context(self, request):
        return TripContextResponse(
            destination=request.destination,
            coordinates=Coordinates(lat=48.137154, lon=11.576124),
            events=[
                EventCandidate(
                    sourceId="serpapi:1",
                    title="Munich Summer Festival",
                    venueName="Olympiapark",
                    dateText="Fri, Jun 5, 7:00 PM",
                    score=40,
                )
            ],
            places=[],
        )


def override_service():
    return FakeTravelContextService()


app.dependency_overrides[get_travel_context_service] = override_service
client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "travel-context-service"}


def test_trip_context_endpoint_returns_events():
    response = client.post(
        "/trip-context",
        json={
            "destination": "Munich",
            "startDate": "2026-06-01",
            "endDate": "2026-06-05",
            "vibe": "cultural",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["destination"] == "Munich"
    assert data["coordinates"]["lat"] == 48.137154
    assert data["events"][0]["title"] == "Munich Summer Festival"
    assert data["places"] == []
