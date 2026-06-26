from __future__ import annotations

import logging
from datetime import date, timedelta

from app.config.settings import settings
from app.models.schemas import (
    EventCandidate,
    GeocodedLocation,
    TripContextRequest,
    TripContextResponse,
    WeatherDaily,
)
from app.services.cache import TtlCache
from app.services.providers.nominatim_provider import NominatimProvider
from app.services.providers.open_meteo_provider import OpenMeteoWeatherProvider
from app.services.providers.overpass_provider import OverpassProvider
from app.services.providers.photon_provider import PhotonProvider
from app.services.providers.serpapi_events_provider import SerpApiEventsProvider
from app.services.ranking import PlaceRanker
from app.observability import get_tracer
from app.metrics import (
    CACHE_REQUESTS_TOTAL,
    EVENTS_RETURNED,
    PROVIDER_DURATION_SECONDS,
    PROVIDER_REQUESTS_TOTAL,
    WEATHER_DAYS_RETURNED,
)

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

COUNTRY_CODE_FALLBACK = "us"
GERMANY_ALIASES = {"de", "deu", "germany", "deutschland"}


class TravelContextService:
    def __init__(
        self,
        geocoder: NominatimProvider | None = None,
        fallback_geocoder: PhotonProvider | None = None,
        place_provider: OverpassProvider | None = None,
        events_provider: SerpApiEventsProvider | None = None,
        weather_provider: OpenMeteoWeatherProvider | None = None,
        geocode_cache: TtlCache[GeocodedLocation] | None = None,
        events_cache: TtlCache[list[EventCandidate]] | None = None,
        weather_cache: TtlCache[list[WeatherDaily]] | None = None,
    ):
        self.geocoder = geocoder or NominatimProvider(
            settings.NOMINATIM_BASE_URL, settings.HTTP_USER_AGENT
        )
        self.fallback_geocoder = fallback_geocoder or PhotonProvider(
            settings.PHOTON_BASE_URL, settings.HTTP_USER_AGENT
        )
        self.place_provider = place_provider or OverpassProvider(
            settings.OVERPASS_BASE_URL, settings.HTTP_USER_AGENT
        )
        self.events_provider = events_provider or SerpApiEventsProvider(
            settings.SERPAPI_BASE_URL, settings.SERPAPI_API_KEY
        )
        self.weather_provider = weather_provider or OpenMeteoWeatherProvider(
            settings.OPEN_METEO_FORECAST_BASE_URL,
            settings.OPEN_METEO_ARCHIVE_BASE_URL,
            settings.WEATHER_FORECAST_MAX_DAYS,
        )
        self.geocode_cache = geocode_cache or TtlCache(settings.CACHE_TTL_SECONDS)
        self.events_cache = events_cache or TtlCache(settings.CACHE_TTL_SECONDS)
        self.weather_cache = weather_cache or TtlCache(settings.CACHE_TTL_SECONDS)
        self.ranker = PlaceRanker()

    async def build_trip_context(
        self, request: TripContextRequest
    ) -> TripContextResponse:
        with tracer.start_as_current_span("travel_context.build") as span:
            span.set_attribute("trip.destination", request.destination)
            span.set_attribute("trip.vibe", request.vibe)
            span.set_attribute("trip.include_events", request.includeEvents)
            logger.info(
                "Building travel context destination=%s startDate=%s endDate=%s vibe=%s includeEvents=%s",
                request.destination,
                request.startDate,
                request.endDate,
                request.vibe,
                request.includeEvents,
            )
            location = await self._geocode(request.destination)
            events = (
                await self._search_events(location, request.startDate, request.endDate)
                if request.includeEvents
                else []
            )
            weather = await self._get_weather(
                location, request.startDate, request.endDate
            )
            span.set_attribute("travel_context.events_count", len(events))
            span.set_attribute("travel_context.weather_days", len(weather))
            EVENTS_RETURNED.observe(len(events))
            WEATHER_DAYS_RETURNED.observe(len(weather))
        logger.info(
            "Built travel context destination=%s validated_location=%s events=%s weather_days=%s",
            request.destination,
            location.name,
            len(events),
            len(weather),
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
            weather=weather,
        )

    async def _geocode(self, destination: str) -> GeocodedLocation:
        with tracer.start_as_current_span("travel_context.geocode") as span:
            span.set_attribute("trip.destination", destination)
            return await self._geocode_observed(destination)

    async def _geocode_observed(self, destination: str) -> GeocodedLocation:
        cache_key = f"geocode:{destination.strip().lower()}"
        cached = self.geocode_cache.get(cache_key)
        if cached:
            CACHE_REQUESTS_TOTAL.labels(cache="geocode", result="hit").inc()
            logger.info(
                "Geocode cache hit destination=%s name=%s country_code=%s lat=%s lon=%s",
                destination,
                cached.name,
                cached.countryCode,
                cached.coordinates.lat,
                cached.coordinates.lon,
            )
            return cached
        CACHE_REQUESTS_TOTAL.labels(cache="geocode", result="miss").inc()
        try:
            logger.info(
                "Geocoding destination with Nominatim destination=%s", destination
            )
            with PROVIDER_DURATION_SECONDS.labels(provider="nominatim").time():
                location = await self.geocoder.geocode(destination)
            PROVIDER_REQUESTS_TOTAL.labels(
                provider="nominatim", outcome="success"
            ).inc()
        except Exception as error:
            PROVIDER_REQUESTS_TOTAL.labels(provider="nominatim", outcome="error").inc()
            logger.warning(
                "Nominatim geocoding failed destination=%s error=%s; trying Photon fallback",
                destination,
                error,
            )
            try:
                with PROVIDER_DURATION_SECONDS.labels(provider="photon").time():
                    location = await self.fallback_geocoder.geocode(destination)
                PROVIDER_REQUESTS_TOTAL.labels(
                    provider="photon", outcome="success"
                ).inc()
            except Exception:
                PROVIDER_REQUESTS_TOTAL.labels(provider="photon", outcome="error").inc()
                raise
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
        with tracer.start_as_current_span("travel_context.search_events") as span:
            span.set_attribute("travel_context.location", location.name)
            return await self._search_events_observed(location, start_date, end_date)

    async def _search_events_observed(
        self,
        location: GeocodedLocation,
        start_date: date,
        end_date: date,
    ) -> list[EventCandidate]:
        location_name = location.name.strip() or location.displayName or ""
        country_code = _google_country_code(location.countryCode)
        date_filter = _date_filter(start_date, end_date)
        cache_key = (
            f"events:{location_name.lower()}:{country_code}:{date_filter or 'any'}"
        )
        cached = self.events_cache.get(cache_key)
        if cached is not None:
            CACHE_REQUESTS_TOTAL.labels(cache="events", result="hit").inc()
            logger.info(
                "Events cache hit location=%s country_code=%s date_filter=%s events=%s",
                location_name,
                country_code,
                date_filter,
                len(cached),
            )
            return cached
        CACHE_REQUESTS_TOTAL.labels(cache="events", result="miss").inc()
        logger.info(
            "Searching events location=%s country_code=%s date_filter=%s",
            location_name,
            country_code,
            date_filter,
        )
        try:
            with PROVIDER_DURATION_SECONDS.labels(provider="serpapi_events").time():
                events = await self.events_provider.search_events(
                    location_name=location_name,
                    country_code=country_code,
                    date_filter=date_filter,
                )
            PROVIDER_REQUESTS_TOTAL.labels(
                provider="serpapi_events", outcome="success"
            ).inc()
        except Exception:
            PROVIDER_REQUESTS_TOTAL.labels(
                provider="serpapi_events", outcome="error"
            ).inc()
            raise
        limited_events = events[: settings.EVENT_SEARCH_LIMIT]
        self.events_cache.set(cache_key, limited_events)
        return limited_events

    async def _get_weather(
        self,
        location: GeocodedLocation,
        start_date: date,
        end_date: date,
    ) -> list[WeatherDaily]:
        with tracer.start_as_current_span("travel_context.weather") as span:
            span.set_attribute("travel_context.location", location.name)
            return await self._get_weather_observed(location, start_date, end_date)

    async def _get_weather_observed(
        self,
        location: GeocodedLocation,
        start_date: date,
        end_date: date,
    ) -> list[WeatherDaily]:
        if not settings.WEATHER_ENABLED:
            return []

        coordinates = location.coordinates
        cache_key = (
            f"weather:{coordinates.lat:.3f}:{coordinates.lon:.3f}:"
            f"{start_date.isoformat()}:{end_date.isoformat()}"
        )
        cached = self.weather_cache.get(cache_key)
        if cached is not None:
            CACHE_REQUESTS_TOTAL.labels(cache="weather", result="hit").inc()
            logger.info(
                "Weather cache hit lat=%s lon=%s start=%s end=%s days=%s",
                coordinates.lat,
                coordinates.lon,
                start_date,
                end_date,
                len(cached),
            )
            return cached
        CACHE_REQUESTS_TOTAL.labels(cache="weather", result="miss").inc()

        try:
            with PROVIDER_DURATION_SECONDS.labels(provider="open_meteo").time():
                weather = await self.weather_provider.get_weather(
                    coordinates=coordinates,
                    start_date=start_date,
                    end_date=end_date,
                    today=date.today(),
                )
            PROVIDER_REQUESTS_TOTAL.labels(
                provider="open_meteo", outcome="success"
            ).inc()
        except Exception as error:
            PROVIDER_REQUESTS_TOTAL.labels(provider="open_meteo", outcome="error").inc()
            # Weather is a best-effort enhancement; never fail the whole context.
            logger.warning(
                "Weather lookup failed lat=%s lon=%s start=%s end=%s error=%s",
                coordinates.lat,
                coordinates.lon,
                start_date,
                end_date,
                error,
            )
            return []

        logger.info(
            "Built weather lat=%s lon=%s start=%s end=%s days=%s sources=%s",
            coordinates.lat,
            coordinates.lon,
            start_date,
            end_date,
            len(weather),
            [day.source for day in weather],
        )
        self.weather_cache.set(cache_key, weather)
        return weather


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
    last_day_next_month = (first_day_next_month + timedelta(days=32)).replace(
        day=1
    ) - timedelta(days=1)
    if start_date >= first_day_next_month and end_date <= last_day_next_month:
        return "date:next_month"
    return None
