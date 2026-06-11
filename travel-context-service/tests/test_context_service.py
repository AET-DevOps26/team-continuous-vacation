from app.models.schemas import Coordinates, EventCandidate, GeocodedLocation, TripContextRequest
from app.services.cache import TtlCache
from app.services.context_service import TravelContextService


class FailingGeocoder:
    async def geocode(self, destination):
        raise RuntimeError("blocked")


class FallbackGeocoder:
    async def geocode(self, destination):
        return GeocodedLocation(
            name="Munich",
            displayName="Munich, Bavaria, Germany",
            countryCode="de",
            coordinates=Coordinates(lat=48.137154, lon=11.576124),
        )


class EventProvider:
    def __init__(self):
        self.calls = []

    async def search_events(self, location_name, country_code, date_filter=None, language="en"):
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
    service = TravelContextService(
        geocoder=FailingGeocoder(),
        fallback_geocoder=FallbackGeocoder(),
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
    )

    location = await service._geocode("Munich")

    assert location.coordinates.lat == 48.137154
    assert location.coordinates.lon == 11.576124


async def test_context_service_returns_events_and_empty_places():
    events_provider = EventProvider()
    service = TravelContextService(
        geocoder=FallbackGeocoder(),
        fallback_geocoder=FallbackGeocoder(),
        events_provider=events_provider,
        geocode_cache=TtlCache(60),
        events_cache=TtlCache(60),
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
