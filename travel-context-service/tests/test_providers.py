from datetime import date, timedelta

import httpx
import pytest

from app.models.schemas import Coordinates
from app.services.providers.nominatim_provider import NominatimProvider
from app.services.providers.open_meteo_provider import OpenMeteoWeatherProvider
from app.services.providers.overpass_provider import OverpassProvider, build_overpass_query
from app.services.providers.photon_provider import PhotonProvider
from app.services.providers.serpapi_events_provider import SerpApiEventsProvider


@pytest.mark.asyncio
async def test_nominatim_response_maps_to_coordinates(monkeypatch):
    captured_params = {}

    async def fake_get(self, url, params=None, headers=None):
        captured_params.update(params)
        return httpx.Response(
            200,
            json=[
                {
                    "lat": "48.137154",
                    "lon": "11.576124",
                    "name": "München",
                    "namedetails": {"name:en": "Munich"},
                    "display_name": "München, Bayern, Deutschland",
                    "address": {"country_code": "de"},
                }
            ],
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = NominatimProvider("https://nominatim.example", "test-agent")

    location = await provider.geocode("Munich")

    assert captured_params["namedetails"] == 1
    assert location.name == "Munich"
    assert location.countryCode == "de"
    assert location.coordinates.lat == 48.137154
    assert location.coordinates.lon == 11.576124


@pytest.mark.asyncio
async def test_nominatim_rate_limit_error_propagates(monkeypatch):
    async def fake_get(self, url, params=None, headers=None):
        return httpx.Response(
            429,
            text="too many requests",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = NominatimProvider("https://nominatim.example", "test-agent")

    with pytest.raises(httpx.HTTPStatusError):
        await provider.geocode("Munich")


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


@pytest.mark.asyncio
async def test_serpapi_events_error_payload_raises(monkeypatch):
    async def fake_get(self, url, params=None):
        return httpx.Response(
            200,
            json={"error": "rate limit exceeded"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = SerpApiEventsProvider("https://serpapi.example/search", "secret-key")

    with pytest.raises(RuntimeError, match="rate limit exceeded"):
        await provider.search_events("Munich", "de")


@pytest.mark.asyncio
async def test_serpapi_events_timeout_propagates(monkeypatch):
    async def fake_get(self, url, params=None):
        raise httpx.TimeoutException("serpapi timed out")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = SerpApiEventsProvider("https://serpapi.example/search", "secret-key")

    with pytest.raises(httpx.TimeoutException, match="serpapi timed out"):
        await provider.search_events("Munich", "de")


def _hourly_payload(start: date, end: date, include_probability: bool) -> dict:
    """Build a deterministic hourly payload: clear all day, thunderstorm 14-17h."""
    times, temps, precipitations, codes, probabilities = [], [], [], [], []
    day = start
    while day <= end:
        for hour in range(24):
            times.append(f"{day.isoformat()}T{hour:02d}:00")
            temps.append(float(hour))
            if 14 <= hour <= 17:
                precipitations.append(5.0)
                codes.append(95)
                probabilities.append(90)
            else:
                precipitations.append(0.0)
                codes.append(0)
                probabilities.append(10)
        day += timedelta(days=1)
    hourly = {
        "time": times,
        "temperature_2m": temps,
        "precipitation": precipitations,
        "weather_code": codes,
    }
    if include_probability:
        hourly["precipitation_probability"] = probabilities
    return {"hourly": hourly}


def _patch_open_meteo(monkeypatch):
    calls = []

    async def fake_get(self, url, params=None):
        calls.append({"url": url, "params": params})
        start = date.fromisoformat(params["start_date"])
        end = date.fromisoformat(params["end_date"])
        include_probability = "precipitation_probability" in params["hourly"]
        return httpx.Response(
            200,
            json=_hourly_payload(start, end, include_probability),
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    return calls


@pytest.mark.asyncio
async def test_open_meteo_forecast_aggregates_hours_into_time_blocks(monkeypatch):
    calls = _patch_open_meteo(monkeypatch)
    provider = OpenMeteoWeatherProvider(
        "https://meteo.example/forecast",
        "https://meteo.example/archive",
        forecast_max_days=16,
    )

    weather = await provider.get_weather(
        coordinates=Coordinates(lat=48.1, lon=11.5),
        start_date=date(2026, 6, 3),
        end_date=date(2026, 6, 3),
        today=date(2026, 6, 1),
    )

    assert len(weather) == 1
    day = weather[0]
    assert day.source == "forecast"
    assert day.date == date(2026, 6, 3)
    assert day.referenceDate is None
    assert day.precipitationProbabilityMax == 90
    assert day.tempMinC == 0.0
    assert day.tempMaxC == 23.0

    blocks = {block.timeBlock: block for block in day.blocks}
    assert blocks["AFTERNOON"].condition == "Thunderstorm"
    assert blocks["AFTERNOON"].precipitationMm == 20.0
    assert blocks["AFTERNOON"].temperatureC == 15.5
    assert blocks["MORNING"].condition == "Clear sky"
    assert blocks["MORNING"].precipitationMm == 0.0

    assert calls[0]["url"] == "https://meteo.example/forecast"


@pytest.mark.asyncio
async def test_open_meteo_falls_back_to_previous_year_for_far_future(monkeypatch):
    calls = _patch_open_meteo(monkeypatch)
    provider = OpenMeteoWeatherProvider(
        "https://meteo.example/forecast",
        "https://meteo.example/archive",
        forecast_max_days=16,
    )

    weather = await provider.get_weather(
        coordinates=Coordinates(lat=48.1, lon=11.5),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 1),
        today=date(2026, 6, 1),
    )

    assert len(weather) == 1
    day = weather[0]
    assert day.source == "historical"
    assert day.date == date(2026, 7, 1)
    assert day.referenceDate == date(2025, 7, 1)
    assert day.precipitationProbabilityMax is None
    assert "2025-07-01" in day.summary

    assert calls[0]["url"] == "https://meteo.example/archive"
    assert calls[0]["params"]["start_date"] == "2025-07-01"


@pytest.mark.asyncio
async def test_open_meteo_mixes_forecast_and_historical_across_boundary(monkeypatch):
    calls = _patch_open_meteo(monkeypatch)
    provider = OpenMeteoWeatherProvider(
        "https://meteo.example/forecast",
        "https://meteo.example/archive",
        forecast_max_days=16,
    )

    # today + 15 .. today + 18, with a 16-day forecast horizon (cutoff at today+16).
    weather = await provider.get_weather(
        coordinates=Coordinates(lat=48.1, lon=11.5),
        start_date=date(2026, 6, 16),
        end_date=date(2026, 6, 19),
        today=date(2026, 6, 1),
    )

    assert [day.source for day in weather] == [
        "forecast",
        "forecast",
        "historical",
        "historical",
    ]
    assert [day.date for day in weather] == [
        date(2026, 6, 16),
        date(2026, 6, 17),
        date(2026, 6, 18),
        date(2026, 6, 19),
    ]
    assert weather[2].referenceDate == date(2025, 6, 18)

    urls = [call["url"] for call in calls]
    assert "https://meteo.example/forecast" in urls
    assert "https://meteo.example/archive" in urls


@pytest.mark.asyncio
async def test_open_meteo_returns_historical_even_if_forecast_segment_fails(monkeypatch):
    calls = []

    async def fake_get(self, url, params=None):
        calls.append(url)
        if "forecast" in url:
            return httpx.Response(
                400,
                json={"error": True, "reason": "end_date out of allowed range"},
                request=httpx.Request("GET", url),
            )
        start = date.fromisoformat(params["start_date"])
        end = date.fromisoformat(params["end_date"])
        return httpx.Response(
            200,
            json=_hourly_payload(start, end, include_probability=False),
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    provider = OpenMeteoWeatherProvider(
        "https://meteo.example/forecast",
        "https://meteo.example/archive",
        forecast_max_days=16,
    )

    # Two forecast days (which fail) and two historical days (which succeed).
    weather = await provider.get_weather(
        coordinates=Coordinates(lat=48.1, lon=11.5),
        start_date=date(2026, 6, 16),
        end_date=date(2026, 6, 19),
        today=date(2026, 6, 1),
    )

    # The forecast 400 must not wipe out the historical days.
    assert [day.source for day in weather] == ["historical", "historical"]
    assert [day.date for day in weather] == [date(2026, 6, 18), date(2026, 6, 19)]


def test_prior_year_clamps_leap_day():
    from app.services.providers.open_meteo_provider import _prior_year

    assert _prior_year(date(2028, 2, 29)) == date(2027, 2, 28)
    assert _prior_year(date(2026, 7, 1)) == date(2025, 7, 1)
