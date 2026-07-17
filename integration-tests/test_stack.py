"""End-to-end flow across backend -> genai-service -> travel-context-service -> Postgres.

Only third-party APIs are faked (see tests/mock-providers). Every service boundary in the request
path is real, so a contract drift between two of our services fails these tests -- which is
exactly what the per-service suites cannot catch, because they stub that boundary out.

The expected titles below are the ones served by tests/mock-providers/server.py. Asserting on
them proves the stub's payload actually travelled genai -> backend -> Postgres -> client rather
than something being generated or defaulted along the way.
"""

import pytest

from conftest import TRIP_DESTINATION, TRIP_END, TRIP_START, TRIP_VIBE

# server.py suffixes each title with the day's date to keep them unique across the schedule,
# which _validate_schedule_contract requires.
STUB_DAY_ONE_TITLES = {f"{name} {TRIP_START}" for name in ("Museum", "City Walk", "Dinner")}
STUB_DAY_TWO_TITLES = {f"{name} {TRIP_END}" for name in ("Museum", "City Walk", "Dinner")}
STUB_ALTERNATIVE_TITLE = "Mock Replacement Activity"


@pytest.fixture(scope="session")
def trip(client, auth_headers):
    """Generate one trip and reuse it: this is the call that crosses every service."""
    response = client.post(
        "/trips",
        headers=auth_headers,
        json={
            "destination": TRIP_DESTINATION,
            "startDate": TRIP_START,
            "endDate": TRIP_END,
            "vibe": TRIP_VIBE,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_login_returns_a_usable_token(client, auth):
    response = client.post(
        "/auth/login", json={"email": auth["email"], "password": auth["password"]}
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["travelerId"] == auth["travelerId"]
    assert body["isDemo"] is False
    assert body["accessToken"]

    # Prove the token works rather than just that it exists.
    authed = client.get("/trips", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert authed.status_code == 200, authed.text


def test_trips_reject_unauthenticated_requests(client):
    assert client.get("/trips").status_code == 401


def test_generate_trip_returns_the_schedule_from_genai(trip):
    assert trip["destination"] == TRIP_DESTINATION
    assert trip["startDate"] == TRIP_START
    assert trip["endDate"] == TRIP_END

    days = trip["schedule"]["days"]
    assert [day["date"] for day in days] == [TRIP_START, TRIP_END]

    assert {a["title"] for a in days[0]["activities"]} == STUB_DAY_ONE_TITLES
    assert {a["title"] for a in days[1]["activities"]} == STUB_DAY_TWO_TITLES


def test_generated_trip_is_persisted(client, auth_headers, trip):
    response = client.get(f"/trips/{trip['id']}", headers=auth_headers)
    assert response.status_code == 200, response.text

    # Round-tripping through Postgres must not lose or reorder the schedule. This compares
    # against the trip as generated, so it has to run before the tests below mutate it --
    # the `trip` fixture is session-scoped and is not refreshed.
    assert response.json() == trip


def test_generated_trip_appears_in_the_traveler_list(client, auth_headers, trip):
    response = client.get("/trips", headers=auth_headers)
    assert response.status_code == 200, response.text

    summaries = {t["id"]: t for t in response.json()}
    assert trip["id"] in summaries
    assert summaries[trip["id"]]["destination"] == TRIP_DESTINATION


def test_regenerate_activity_replaces_it_via_genai(client, auth_headers, trip):
    day = trip["schedule"]["days"][0]
    activity = day["activities"][0]

    response = client.patch(
        f"/trips/{trip['id']}/days/{day['id']}/activities/{activity['id']}",
        headers=auth_headers,
        json={"instruction": "Something indoors instead, please."},
    )
    assert response.status_code == 200, response.text
    assert response.json()["title"] == STUB_ALTERNATIVE_TITLE

    # The replacement must survive to the database, not just come back in the response.
    stored = client.get(f"/trips/{trip['id']}", headers=auth_headers)
    assert stored.status_code == 200, stored.text
    stored_day = next(d for d in stored.json()["schedule"]["days"] if d["id"] == day["id"])
    assert STUB_ALTERNATIVE_TITLE in {a["title"] for a in stored_day["activities"]}


def test_deleting_an_activity_removes_it(client, auth_headers, trip):
    day = trip["schedule"]["days"][1]
    activity = day["activities"][0]

    response = client.delete(
        f"/trips/{trip['id']}/days/{day['id']}/activities/{activity['id']}",
        headers=auth_headers,
    )
    assert response.status_code == 204, response.text

    stored = client.get(f"/trips/{trip['id']}", headers=auth_headers)
    stored_day = next(d for d in stored.json()["schedule"]["days"] if d["id"] == day["id"])
    assert activity["id"] not in {a["id"] for a in stored_day["activities"]}
