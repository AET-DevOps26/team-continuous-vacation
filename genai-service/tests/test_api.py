from fastapi.testclient import TestClient
from uuid import UUID
from app.api.routes.schedules import get_schedule_service
from app.main import app
from app.services.schedule_service import ScheduleService


class NullTravelContextClient:
    async def get_trip_context(self, preferences, include_events=True):
        return None


class FakeLLMProvider:
    async def generate(self, prompt, options):
        if "replacement activity" in prompt:
            return """
            {
              "timeBlock": "MORNING",
              "title": "Indoor climbing session",
              "description": "Try a guided indoor climbing class with rented equipment.",
              "durationMinutes": 120,
              "isIndoor": true,
              "tags": ["SPORTY", "INDOOR"]
            }
            """

        return """
        {
          "days": [
            {
              "dayNumber": 1,
              "date": "2026-05-15",
              "activities": [
                {
                  "timeBlock": "MORNING",
                  "title": "English Garden running route",
                  "description": "Start the trip with a scenic active route through Munich's largest park.",
                  "durationMinutes": 90,
                  "isIndoor": false,
                  "tags": ["SPORTY", "ENTERTAINMENT", "SURPRISE_ME"]
                },
                {
                  "timeBlock": "AFTERNOON",
                  "title": "Olympiapark stadium tour",
                  "description": "Explore the Olympic grounds with active walking between the main venues.",
                  "durationMinutes": 120,
                  "isIndoor": false,
                  "tags": ["SPORTY", "CULTURAL"]
                },
                {
                  "timeBlock": "EVENING",
                  "title": "Healthy Bavarian dinner",
                  "description": "Recover with a hearty local meal after the first active day.",
                  "durationMinutes": 90,
                  "isIndoor": true,
                  "tags": ["FOOD", "RELAXING"]
                }
              ]
            },
            {
              "dayNumber": 2,
              "date": "2026-05-16",
              "activities": [
                {
                  "timeBlock": "MORNING",
                  "title": "Olympiapark bike loop",
                  "description": "Cycle past the Olympic venues and lake paths at an easy pace.",
                  "durationMinutes": 120,
                  "isIndoor": false,
                  "tags": ["SPORTY", "OUTDOOR"]
                },
                {
                  "timeBlock": "AFTERNOON",
                  "title": "Boulderwelt technique class",
                  "description": "Join a coached climbing session focused on movement and balance.",
                  "durationMinutes": 120,
                  "isIndoor": true,
                  "tags": ["SPORTY", "INDOOR"]
                },
                {
                  "timeBlock": "EVENING",
                  "title": "Isar picnic walk",
                  "description": "Take a relaxed riverside walk with a light picnic stop.",
                  "durationMinutes": 90,
                  "isIndoor": false,
                  "tags": ["RELAXING", "OUTDOOR"]
                }
              ]
            },
            {
              "dayNumber": 3,
              "date": "2026-05-17",
              "activities": [
                {
                  "timeBlock": "MORNING",
                  "title": "Isar river fitness walk",
                  "description": "Follow the river paths with stops for stretching and city views.",
                  "durationMinutes": 100,
                  "isIndoor": false,
                  "tags": ["SPORTY", "OUTDOOR"]
                },
                {
                  "timeBlock": "AFTERNOON",
                  "title": "Deutsches Museum active science visit",
                  "description": "Choose interactive exhibits and hands-on areas for an energetic museum session.",
                  "durationMinutes": 150,
                  "isIndoor": true,
                  "tags": ["CULTURAL", "INDOOR"]
                },
                {
                  "timeBlock": "EVENING",
                  "title": "Schwabing food stroll",
                  "description": "Sample casual local spots while walking through the lively district.",
                  "durationMinutes": 120,
                  "isIndoor": false,
                  "tags": ["FOOD", "CULTURAL"]
                }
              ]
            },
            {
              "dayNumber": 4,
              "date": "2026-05-18",
              "activities": [
                {
                  "timeBlock": "MORNING",
                  "title": "Guided bouldering finale",
                  "description": "Wrap up with a beginner-friendly bouldering session in the city.",
                  "durationMinutes": 120,
                  "isIndoor": true,
                  "tags": ["SPORTY", "INDOOR"]
                },
                {
                  "timeBlock": "AFTERNOON",
                  "title": "Nymphenburg garden walk",
                  "description": "Finish with a scenic walk through palace gardens and quiet paths.",
                  "durationMinutes": 120,
                  "isIndoor": false,
                  "tags": ["CULTURAL", "OUTDOOR"]
                },
                {
                  "timeBlock": "EVENING",
                  "title": "Farewell Viktualienmarkt tasting",
                  "description": "Enjoy a compact food-focused finale near the old town.",
                  "durationMinutes": 90,
                  "isIndoor": false,
                  "tags": ["FOOD", "RELAXING"]
                }
              ]
            }
          ]
        }
        """


def override_schedule_service():
    return ScheduleService(
        llm_provider=FakeLLMProvider(),
        travel_context_client=NullTravelContextClient(),
    )


app.dependency_overrides[get_schedule_service] = override_schedule_service

client = TestClient(app)


def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "genai-service"


def test_root_endpoint():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "GenAI Service"
    assert response.json()["status"] == "running"


def test_generate_schedule():
    """Test the schedule generation endpoint (OpenAPI spec)"""
    request_data = {
        "destination": "Munich",
        "startDate": "2026-05-15",
        "endDate": "2026-05-18",
        "vibe": "Sporty and active",
    }

    response = client.post("/schedules", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "days" in data
    assert isinstance(data["days"], list)
    assert len(data["days"]) == 4  # 4 days between May 15 and May 18

    # Verify day structure
    first_day = data["days"][0]
    assert set(first_day) == {"id", "dayNumber", "date", "activities"}
    UUID(first_day["id"])
    assert isinstance(first_day["activities"], list)

    # Verify activity structure
    if len(first_day["activities"]) > 0:
        activity = first_day["activities"][0]
        assert set(activity) == {
            "id",
            "dayId",
            "timeBlock",
            "title",
            "description",
            "durationMinutes",
            "isIndoor",
            "tags",
        }
        UUID(activity["id"])
        assert activity["dayId"] == first_day["id"]
        assert "ENTERTAINMENT" in activity["tags"]
        assert "SURPRISE_ME" not in activity["tags"]


def test_suggest_alternative_activity():
    """Test the alternative activity suggestion endpoint (OpenAPI spec)"""
    request_data = {
        "instruction": "Make this an indoor activity",
        "activity": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "dayId": "550e8400-e29b-41d4-a716-446655440001",
            "timeBlock": "MORNING",
            "title": "Walking tour",
            "description": "Outdoor walking tour",
            "durationMinutes": 120,
            "isIndoor": False,
            "tags": ["OUTDOOR", "CULTURAL"],
        },
        "tripContext": {
            "destination": "Munich",
            "startDate": "2026-05-15",
            "endDate": "2026-05-18",
            "vibe": "Sporty and active",
            "days": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "dayNumber": 1,
                    "date": "2026-05-15",
                    "activities": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "dayId": "550e8400-e29b-41d4-a716-446655440001",
                            "timeBlock": "MORNING",
                            "title": "Walking tour",
                            "description": "Outdoor walking tour",
                            "durationMinutes": 120,
                            "isIndoor": False,
                            "tags": ["OUTDOOR", "CULTURAL"],
                        }
                    ],
                }
            ],
        },
    }

    response = client.post("/activities/alternative", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert set(data) == {
        "id",
        "dayId",
        "timeBlock",
        "title",
        "description",
        "durationMinutes",
        "isIndoor",
        "tags",
    }
    UUID(data["id"])
    assert data["dayId"] == request_data["activity"]["dayId"]


def test_generation_preferences_accepts_seven_day_trip():
    from app.models.schemas import GenerationPreferences

    preferences = GenerationPreferences(
        destination="Munich",
        startDate="2026-05-15",
        endDate="2026-05-21",
        vibe="cultural",
    )

    assert preferences.startDate.isoformat() == "2026-05-15"
    assert preferences.endDate.isoformat() == "2026-05-21"


def test_generate_schedule_rejects_eight_day_trip():
    response = client.post(
        "/schedules",
        json={
            "destination": "Munich",
            "startDate": "2026-05-15",
            "endDate": "2026-05-22",
            "vibe": "cultural",
        },
    )

    assert response.status_code == 422


def test_generate_schedule_rejects_reversed_dates():
    response = client.post(
        "/schedules",
        json={
            "destination": "Munich",
            "startDate": "2026-05-18",
            "endDate": "2026-05-15",
            "vibe": "cultural",
        },
    )

    assert response.status_code == 422


def test_generate_schedule_rejects_oversized_and_extra_fields():
    base = {
        "destination": "M" * 201,
        "startDate": "2026-05-15",
        "endDate": "2026-05-18",
        "vibe": "cultural",
    }
    assert client.post("/schedules", json=base).status_code == 422

    base["destination"] = "Munich"
    base["unexpected"] = True
    assert client.post("/schedules", json=base).status_code == 422


def test_alternative_rejects_activity_outside_parent_day():
    activity = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "dayId": "550e8400-e29b-41d4-a716-446655440099",
        "timeBlock": "MORNING",
        "title": "Walking tour",
        "description": "Outdoor walking tour",
        "durationMinutes": 120,
        "isIndoor": False,
        "tags": ["OUTDOOR"],
    }
    response = client.post(
        "/activities/alternative",
        json={
            "instruction": "Make this indoor",
            "activity": activity,
            "tripContext": {
                "destination": "Munich",
                "startDate": "2026-05-15",
                "endDate": "2026-05-15",
                "vibe": "cultural",
                "days": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "dayNumber": 1,
                        "date": "2026-05-15",
                        "activities": [activity],
                    }
                ],
            },
        },
    )

    assert response.status_code == 422


def test_internal_api_does_not_emit_cors_headers():
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
