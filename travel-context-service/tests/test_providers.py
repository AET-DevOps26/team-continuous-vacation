import httpx
import pytest

from app.services.providers.nominatim_provider import NominatimProvider
from app.services.providers.overpass_provider import OverpassProvider, build_overpass_query
from app.services.providers.photon_provider import PhotonProvider
from app.services.providers.serpapi_events_provider import SerpApiEventsProvider


@pytest.mark.asyncio
async def test_nominatim_response_maps_to_coordinates(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "48.137154",
                    "lon": "11.576124",
                    "name": "München",
                    "display_name": "München, Bayern, Deutschland",
                    "address": {"country_code": "de"},
                }
            ],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = NominatimProvider("https://nominatim.example", "test-agent")

    location = await provider.geocode("Munich")

    assert location.name == "München"
    assert location.countryCode == "de"
    assert location.coordinates.lat == 48.137154
    assert location.coordinates.lon == 11.576124


@pytest.mark.asyncio
async def test_overpass_maps_nodes_ways_and_relations(monkeypatch):
    async def fake_post(self, url, content=None, headers=None):
        return httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type": "node",
                        "id": 1,
                        "lat": 48.1,
                        "lon": 11.5,
                        "tags": {"name": "Marienplatz", "place": "square"},
                    },
                    {
                        "type": "way",
                        "id": 2,
                        "center": {"lat": 48.2, "lon": 11.6},
                        "tags": {"name": "Englischer Garten", "leisure": "park"},
                    },
                    {
                        "type": "relation",
                        "id": 3,
                        "center": {"lat": 48.3, "lon": 11.7},
                        "tags": {"name": "Tierpark Hellabrunn", "tourism": "zoo"},
                    },
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    provider = OverpassProvider("https://overpass.example", "test-agent")

    places = await provider.search_places(48.13, 11.57, 12000)

    assert [place.name for place in places] == [
        "Marienplatz",
        "Englischer Garten",
        "Tierpark Hellabrunn",
    ]
    assert places[1].latitude == 48.2
    assert places[2].longitude == 11.7


def test_overpass_query_uses_radius_and_expected_tags():
    query = build_overpass_query(48.137154, 11.576124, 12000)

    assert "[out:json][timeout:12];" in query
    assert "around:12000,48.137154,11.576124" in query
    assert '"place"="square"' in query
    assert '"tourism"~"attraction|museum|gallery|viewpoint|zoo|artwork|theme_park"' in query
    assert '"waterway"~"river|stream"' in query


@pytest.mark.asyncio
async def test_photon_response_maps_to_coordinates(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {
                            "coordinates": [11.576124, 48.137154],
                        },
                        "properties": {"name": "München", "countrycode": "DE"},
                    }
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = PhotonProvider("https://photon.example", "test-agent")

    location = await provider.geocode("Munich")

    assert location.name == "München"
    assert location.countryCode == "de"
    assert location.coordinates.lat == 48.137154
    assert location.coordinates.lon == 11.576124


@pytest.mark.asyncio
async def test_serpapi_events_response_maps_to_event_candidates(monkeypatch):
    captured_params = {}

    async def fake_get(self, url, params=None):
        captured_params.update(params)
        return httpx.Response(
            200,
            json={
                "events_results": [
                    {
                        "title": "Munich Summer Festival",
                        "date": {"start_date": "Jun 5", "when": "Fri, Jun 5, 7:00 PM"},
                        "address": ["Olympiapark", "Munich"],
                        "link": "https://example.invalid/event",
                        "description": "Outdoor music and food festival.",
                        "ticket_info": [
                            {
                                "source": "Example Tickets",
                                "link": "https://example.invalid/tickets",
                                "link_type": "tickets",
                            }
                        ],
                        "venue": {"name": "Olympiapark"},
                        "thumbnail": "https://example.invalid/thumb.jpg",
                    }
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = SerpApiEventsProvider("https://serpapi.example/search", "secret-key")

    events = await provider.search_events("Munich", "de", "date:week")

    assert captured_params["engine"] == "google_events"
    assert captured_params["q"] == "Events in Munich"
    assert captured_params["location"] == "Munich"
    assert captured_params["gl"] == "de"
    assert captured_params["htichips"] == "date:week"
    assert captured_params["api_key"] == "secret-key"
    assert events[0].title == "Munich Summer Festival"
    assert events[0].venueName == "Olympiapark"
    assert events[0].ticketLinks[0].linkType == "tickets"
    assert events[0].score > 0


@pytest.mark.asyncio
async def test_serpapi_events_returns_empty_when_api_key_missing():
    provider = SerpApiEventsProvider("https://serpapi.example/search", "")

    events = await provider.search_events("Munich", "de")

    assert events == []
