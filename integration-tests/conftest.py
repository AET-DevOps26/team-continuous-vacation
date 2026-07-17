import os
import uuid

import httpx
import pytest

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:3000")

# Fixed rather than relative to today. genai-service validates that the generated schedule's
# dates match the requested ones exactly, so the LLM stub has to hardcode the same dates --
# which only works if the request does too. Nothing in either service constrains trips to the
# future, and travel-context's date-sensitive path (weather) is stubbed empty, so pinning
# these costs no coverage and keeps the stub from rotting as the calendar moves.
TRIP_START = "2026-06-01"
TRIP_END = "2026-06-02"

# The keyword rules in context_relevance.py short-circuit the classifier on a "city" signal.
# That path is the one worth exercising, and llm-context-relevance.json covers the fallback.
TRIP_DESTINATION = "Munich"
TRIP_VIBE = "cultural city trip"


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=f"{GATEWAY_URL}/api", timeout=90.0) as http_client:
        yield http_client


@pytest.fixture(scope="session")
def auth(client):
    """Register a throwaway traveler and return their auth payload."""
    email = f"ci-{uuid.uuid4().hex[:12]}@example.invalid"
    password = "ci-integration-password"

    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text

    body = response.json()
    return {"email": email, "password": password, **body}


@pytest.fixture(scope="session")
def auth_headers(auth):
    return {"Authorization": f"Bearer {auth['accessToken']}"}
