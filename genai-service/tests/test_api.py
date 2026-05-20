from fastapi.testclient import TestClient
from app.api.routes.schedules import get_schedule_service
from app.main import app
from app.services.schedule_service import ScheduleService


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
                  "tags": ["SPORTY", "OUTDOOR"]
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
    return ScheduleService(llm_provider=FakeLLMProvider())


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
    assert "id" in first_day
    assert "dayNumber" in first_day
    assert "date" in first_day
    assert "activities" in first_day
    assert isinstance(first_day["activities"], list)

    # Verify activity structure
    if len(first_day["activities"]) > 0:
        activity = first_day["activities"][0]
        assert "id" in activity
        assert "dayId" in activity
        assert "timeBlock" in activity
        assert "title" in activity
        assert "description" in activity
        assert "durationMinutes" in activity


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
    assert "id" in data
    assert "dayId" in data
    assert "timeBlock" in data
    assert "title" in data
    assert "description" in data
    assert "durationMinutes" in data
