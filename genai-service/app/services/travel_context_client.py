import logging
from typing import Optional

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config.settings import settings
from app.models.schemas import GenerationPreferences
from app.observability import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class Coordinates(BaseModel):
    lat: float
    lon: float


class TicketLink(BaseModel):
    source: Optional[str] = None
    link: str
    linkType: Optional[str] = None

    @field_validator("link")
    @classmethod
    def validate_link(cls, value: str) -> str:
        return _http_url(value)


class EventCandidate(BaseModel):
    source: str = "serpapi_google_events"
    sourceId: str
    title: str
    description: Optional[str] = None
    dateText: Optional[str] = None
    startDate: Optional[str] = None
    when: Optional[str] = None
    venueName: Optional[str] = None
    address: list[str] = Field(default_factory=list)
    link: Optional[str] = None
    ticketLinks: list[TicketLink] = Field(default_factory=list)
    thumbnail: Optional[str] = None
    score: float = 0.0

    @field_validator("link", "thumbnail")
    @classmethod
    def validate_optional_link(cls, value: Optional[str]) -> Optional[str]:
        return _http_url(value) if value is not None else None


class WeatherBlock(BaseModel):
    timeBlock: str
    condition: str
    temperatureC: Optional[float] = None
    precipitationMm: float = 0.0


class WeatherDaily(BaseModel):
    date: str
    source: str
    referenceDate: Optional[str] = None
    summary: str
    tempMinC: Optional[float] = None
    tempMaxC: Optional[float] = None
    precipitationProbabilityMax: Optional[int] = None
    blocks: list[WeatherBlock] = Field(default_factory=list)


class TravelContext(BaseModel):
    destination: str
    coordinates: Coordinates
    events: list[EventCandidate] = Field(default_factory=list)
    weather: list[WeatherDaily] = Field(default_factory=list)


class TravelContextClient:
    def __init__(
        self,
        base_url: str = settings.TRAVEL_CONTEXT_BASE_URL,
        timeout_seconds: float = settings.TRAVEL_CONTEXT_TIMEOUT_SECONDS,
        enabled: bool = settings.TRAVEL_CONTEXT_ENABLED,
        client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.client = (
            client
            if client is not None
            else httpx.AsyncClient(timeout=self.timeout_seconds)
            if enabled
            else None
        )
        self._owns_client = client is None and self.client is not None

    async def get_trip_context(
        self,
        preferences: GenerationPreferences,
        include_events: bool = True,
    ) -> Optional[TravelContext]:
        if not self.enabled:
            return None
        if self.client is None:
            raise RuntimeError("Enabled travel-context client has no HTTP client")

        payload = {
            "destination": preferences.destination,
            "startDate": preferences.startDate.isoformat(),
            "endDate": preferences.endDate.isoformat(),
            "vibe": preferences.vibe,
            "includeEvents": include_events,
        }
        try:
            with tracer.start_as_current_span("genai.travel_context_request") as span:
                span.set_attribute("trip.destination", preferences.destination)
                span.set_attribute("trip.include_events", include_events)
                span.set_attribute("peer.service", "travel-context-service")
                response = await self.client.post(
                    f"{self.base_url}/trip-context", json=payload
                )
                response.raise_for_status()
                return TravelContext.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            logger.warning(
                "Travel context lookup failed destination=%s error=%s",
                preferences.destination,
                error,
            )
            return None

    async def aclose(self) -> None:
        if self._owns_client and self.client is not None and hasattr(self.client, "aclose"):
            await self.client.aclose()


def _http_url(value: str) -> str:
    if not value.startswith(("http://", "https://")):
        raise ValueError("URL must use http or https")
    return value
