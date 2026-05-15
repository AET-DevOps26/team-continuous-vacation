import pytest
from fastapi.testclient import TestClient
from app.main import app

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
        "vibe": "Sporty and active"
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
            "tags": ["OUTDOOR", "CULTURAL"]
        },
        "tripContext": {
            "destination": "Munich",
            "startDate": "2026-05-15",
            "endDate": "2026-05-18",
            "vibe": "Sporty and active",
            "days": [{
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "dayNumber": 1,
                "date": "2026-05-15",
                "activities": [{
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "dayId": "550e8400-e29b-41d4-a716-446655440001",
                    "timeBlock": "MORNING",
                    "title": "Walking tour",
                    "description": "Outdoor walking tour",
                    "durationMinutes": 120,
                    "isIndoor": False,
                    "tags": ["OUTDOOR", "CULTURAL"]
                }]
            }]
        }
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
