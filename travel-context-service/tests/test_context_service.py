from prometheus_client import REGISTRY, generate_latest

from app.models.schemas import (
    Coordinates,
    EventCandidate,
    GeocodedLocation,
    TripContextRequest,
    WeatherBlock,
    WeatherDaily,
)
from app.services.cache import TtlCache
from app.services.context_service import TravelContextService


class FailingGeocoder:
    async def geocode(self, destination):
        raise RuntimeError("blocked")


class FakeWeatherProvider:
    def __init__(self):
        self.calls = []

    async def get_weather(self, coordinates, start_date, end_date, today):
        self.calls.append(
            {
                "coordinates": coordinates,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return [
            WeatherDaily(
                date=start_date,
                source="forecast",
                summary="Thunderstorm, 14-22°C",
                tempMinC=14.0,
                tempMaxC=22.0,
                precipitationProbabilityMax=80,
                blocks=[
                    WeatherBlock(
                        timeBlock="AFTERNOON",
                        condition="Thunderstorm",
                        temperatureC=20.0,
                        precipitationMm=8.0,
                    )
                ],
            )
        ]


class FallbackGeocoder:
    def __init__(self):
        self.calls = 0

    async def geocode(self, destination):
        self.calls += 1
        return GeocodedLocation(
            name="Munich",
            displayName="Munich, Bavaria, Germany",
            countryCode="de",
            coordinates=Coordinates(lat=48.137154, lon=11.576124),
        )


class EventProvider:
    def __init__(self):
        self.calls = []

    async def search_events(
        self, location_name, country_code, date_filter=None, language="en"
    ):
        self.calls.append(
            {
                "location_name": location_name,
                "country_code": country_code,
                "date_filter": date_filter,
                "language": language,
            }
        )
        return [
            EventCandidate(
                sourceId="serpapi:1",
                title="Munich Summer Festival",
                venueName="Olympiapark",
                dateText="Fri, Jun 5, 7:00 PM",
                score=40,
            )
        ]


async def test_context_service_uses_photon_fallback_when_nominatim_fails():
    fallback_geocoder = FallbackGeocoder()
    service = TravelContextService(
        geocoder=FailingGeocoder(),
        fallback_geocoder=fallback_geocoder,
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
    )

    location = await service._geocode("Munich")

    assert location.coordinates.lat == 48.137154
    assert location.coordinates.lon == 11.576124
    assert fallback_geocoder.calls == 1
    metrics = generate_latest(REGISTRY).decode("utf-8")
    assert (
        'travel_context_provider_requests_total{outcome="error",provider="nominatim"}'
        in metrics
    )
    assert (
        'travel_context_provider_requests_total{outcome="success",provider="photon"}'
        in metrics
    )


async def test_context_service_reuses_geocode_cache():
    geocoder = FallbackGeocoder()
    service = TravelContextService(
        geocoder=geocoder,
        fallback_geocoder=FallbackGeocoder(),
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
    )

    first = await service._geocode("Munich")
    second = await service._geocode("munich")

    assert first == second
    assert geocoder.calls == 1


async def test_context_service_returns_events_and_empty_places():
    events_provider = EventProvider()
    service = TravelContextService(
        geocoder=FallbackGeocoder(),
        fallback_geocoder=FallbackGeocoder(),
        events_provider=events_provider,
        weather_provider=FakeWeatherProvider(),
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
        weather_cache=TtlCache(60),
    )

    response = await service.build_trip_context(
        TripContextRequest(
            destination="Munich",
            startDate="2026-06-01",
            endDate="2026-06-03",
            vibe="cultural",
        )
    )

    assert response.coordinates.lat == 48.137154
    assert response.events[0].title == "Munich Summer Festival"
    assert response.places == []
    assert events_provider.calls[0]["location_name"] == "Munich"
    assert events_provider.calls[0]["country_code"] == "de"
    metrics = generate_latest(REGISTRY).decode("utf-8")
    assert (
        'travel_context_provider_requests_total{outcome="success",provider="nominatim"}'
        in metrics
    )
    assert (
        'travel_context_provider_requests_total{outcome="success",provider="serpapi_events"}'
        in metrics
    )
    assert (
        'travel_context_provider_requests_total{outcome="success",provider="open_meteo"}'
        in metrics
    )
    assert (
        'travel_context_cache_requests_total{cache="geocode",result="miss"}' in metrics
    )
    assert 'travel_context_events_returned_bucket{le="1.0"}' in metrics
    assert 'travel_context_weather_days_returned_bucket{le="1.0"}' in metrics


async def test_context_service_always_returns_weather():
    weather_provider = FakeWeatherProvider()
    service = TravelContextService(
        geocoder=FallbackGeocoder(),
        fallback_geocoder=FallbackGeocoder(),
        events_provider=EventProvider(),
        weather_provider=weather_provider,
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
        weather_cache=TtlCache(60),
    )

    response = await service.build_trip_context(
        TripContextRequest(
            destination="Munich",
            startDate="2026-06-01",
            endDate="2026-06-03",
            vibe="cultural",
        )
    )

    assert len(weather_provider.calls) == 1
    assert response.weather[0].blocks[0].condition == "Thunderstorm"
    assert response.weather[0].blocks[0].timeBlock == "AFTERNOON"
    assert response.weather[0].precipitationProbabilityMax == 80


async def test_context_service_skips_events_but_keeps_weather_when_disabled():
    events_provider = EventProvider()
    weather_provider = FakeWeatherProvider()
    service = TravelContextService(
        geocoder=FallbackGeocoder(),
        fallback_geocoder=FallbackGeocoder(),
        events_provider=events_provider,
        weather_provider=weather_provider,
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
        weather_cache=TtlCache(60),
    )

    response = await service.build_trip_context(
        TripContextRequest(
            destination="Mallorca",
            startDate="2026-06-01",
            endDate="2026-06-03",
            vibe="beach vacation",
            includeEvents=False,
        )
    )

    assert events_provider.calls == []
    assert response.events == []
    assert len(weather_provider.calls) == 1
    assert response.weather[0].summary.startswith("Thunderstorm")


async def test_context_service_weather_is_best_effort_on_failure():
    class FailingWeatherProvider:
        async def get_weather(self, coordinates, start_date, end_date, today):
            raise RuntimeError("weather down")

    service = TravelContextService(
        geocoder=FallbackGeocoder(),
        fallback_geocoder=FallbackGeocoder(),
        events_provider=EventProvider(),
        weather_provider=FailingWeatherProvider(),
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
        weather_cache=TtlCache(60),
    )

    response = await service.build_trip_context(
        TripContextRequest(
            destination="Munich",
            startDate="2026-06-01",
            endDate="2026-06-03",
            vibe="cultural",
        )
    )

    assert response.weather == []
    assert response.events[0].title == "Munich Summer Festival"
