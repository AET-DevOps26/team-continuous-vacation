from __future__ import annotations

import logging
from datetime import date, timedelta

from app.config.settings import settings
from app.models.schemas import EventCandidate, GeocodedLocation, TripContextRequest, TripContextResponse
from app.services.cache import TtlCache
from app.services.providers.nominatim_provider import NominatimProvider
from app.services.providers.overpass_provider import OverpassProvider
from app.services.providers.photon_provider import PhotonProvider
from app.services.providers.serpapi_events_provider import SerpApiEventsProvider
from app.services.ranking import PlaceRanker

logger = logging.getLogger(__name__)

COUNTRY_CODE_FALLBACK = "us"
GERMANY_ALIASES = {"de", "deu", "germany", "deutschland"}


class TravelContextService:
    def __init__(
        self,
        geocoder: NominatimProvider | None = None,
        fallback_geocoder: PhotonProvider | None = None,
        place_provider: OverpassProvider | None = None,
        events_provider: SerpApiEventsProvider | None = None,
        geocode_cache: TtlCache[GeocodedLocation] | None = None,
        events_cache: TtlCache[list[EventCandidate]] | None = None,
    ):
        self.geocoder = geocoder or NominatimProvider(settings.NOMINATIM_BASE_URL, settings.HTTP_USER_AGENT)
        self.fallback_geocoder = fallback_geocoder or PhotonProvider(settings.PHOTON_BASE_URL, settings.HTTP_USER_AGENT)
        self.place_provider = place_provider or OverpassProvider(settings.OVERPASS_BASE_URL, settings.HTTP_USER_AGENT)
        self.events_provider = events_provider or SerpApiEventsProvider(settings.SERPAPI_BASE_URL, settings.SERPAPI_API_KEY)
        self.geocode_cache = geocode_cache or TtlCache(settings.CACHE_TTL_SECONDS)
        self.events_cache = events_cache or TtlCache(settings.CACHE_TTL_SECONDS)
        self.ranker = PlaceRanker()

    async def build_trip_context(self, request: TripContextRequest) -> TripContextResponse:
        logger.info(
            "Building travel context destination=%s startDate=%s endDate=%s vibe=%s",
            request.destination,
            request.startDate,
            request.endDate,
            request.vibe,
        )
        location = await self._geocode(request.destination)
        events = await self._search_events(location, request.startDate, request.endDate)
        logger.info(
            "Built travel context destination=%s validated_location=%s events=%s",
            request.destination,
            location.name,
            len(events),
        )
        logger.info(
            "Top events destination=%s events=%s",
            request.destination,
            [
                {
                    "title": event.title,
                    "venueName": event.venueName,
                    "dateText": event.dateText,
                    "score": event.score,
                    "sourceId": event.sourceId,
                }
                for event in events[:10]
            ],
        )
        return TripContextResponse(
            destination=request.destination,
            coordinates=location.coordinates,
            events=events,
            places=[],
        )

    async def _geocode(self, destination: str) -> GeocodedLocation:
        cache_key = f"geocode:{destination.strip().lower()}"
        cached = self.geocode_cache.get(cache_key)
        if cached:
            logger.info(
                "Geocode cache hit destination=%s name=%s country_code=%s lat=%s lon=%s",
                destination,
                cached.name,
                cached.countryCode,
                cached.coordinates.lat,
                cached.coordinates.lon,
            )
            return cached
        try:
            logger.info("Geocoding destination with Nominatim destination=%s", destination)
            location = await self.geocoder.geocode(destination)
        except Exception as error:
            logger.warning(
                "Nominatim geocoding failed destination=%s error=%s; trying Photon fallback",
                destination,
                error,
            )
            location = await self.fallback_geocoder.geocode(destination)
        logger.info(
            "Geocoded destination=%s name=%s display_name=%r country_code=%s lat=%s lon=%s",
            destination,
            location.name,
            location.displayName,
            location.countryCode,
            location.coordinates.lat,
            location.coordinates.lon,
        )
        self.geocode_cache.set(cache_key, location)
        return location

    async def _search_events(
        self,
        location: GeocodedLocation,
        start_date: date,
        end_date: date,
    ) -> list[EventCandidate]:
        location_name = location.name.strip() or location.displayName or ""
        country_code = _google_country_code(location.countryCode)
        date_filter = _date_filter(start_date, end_date)
        cache_key = f"events:{location_name.lower()}:{country_code}:{date_filter or 'any'}"
        cached = self.events_cache.get(cache_key)
        if cached is not None:
            logger.info(
                "Events cache hit location=%s country_code=%s date_filter=%s events=%s",
                location_name,
                country_code,
                date_filter,
                len(cached),
            )
            return cached
        logger.info(
            "Searching events location=%s country_code=%s date_filter=%s",
            location_name,
            country_code,
            date_filter,
        )
        events = await self.events_provider.search_events(
            location_name=location_name,
            country_code=country_code,
            date_filter=date_filter,
        )
        limited_events = events[: settings.EVENT_SEARCH_LIMIT]
        self.events_cache.set(cache_key, limited_events)
        return limited_events


def _google_country_code(country_code: str | None) -> str:
    normalized = (country_code or "").lower().strip()
    if normalized in GERMANY_ALIASES:
        return "de"
    if len(normalized) == 2:
        return normalized
    return COUNTRY_CODE_FALLBACK


def _date_filter(start_date: date, end_date: date) -> str | None:
    today = date.today()
    if start_date == today and end_date == today:
        return "date:today"
    if start_date == today + timedelta(days=1) and end_date == start_date:
        return "date:tomorrow"
    if start_date <= today <= end_date and (end_date - today).days <= 7:
        return "date:week"
    if start_date <= today <= end_date and (end_date - today).days <= 31:
        return "date:month"
    first_day_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    last_day_next_month = (first_day_next_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    if start_date >= first_day_next_month and end_date <= last_day_next_month:
        return "date:next_month"
    return None
