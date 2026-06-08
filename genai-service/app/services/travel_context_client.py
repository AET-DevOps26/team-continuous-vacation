import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.models.schemas import GenerationPreferences

logger = logging.getLogger(__name__)


class Coordinates(BaseModel):
    lat: float
    lon: float


class PlaceCandidate(BaseModel):
    source: str
    sourceId: str
    name: str
    category: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    website: Optional[str] = None
    wikipedia: Optional[str] = None
    openingHours: Optional[str] = None
    osmTags: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0


class TicketLink(BaseModel):
    source: Optional[str] = None
    link: str
    linkType: Optional[str] = None


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


class TravelContext(BaseModel):
    destination: str
    coordinates: Coordinates
    events: list[EventCandidate] = Field(default_factory=list)
    places: list[PlaceCandidate] = Field(default_factory=list)


class TravelContextClient:
    def __init__(
        self,
        base_url: str = settings.TRAVEL_CONTEXT_BASE_URL,
        timeout_seconds: float = settings.TRAVEL_CONTEXT_TIMEOUT_SECONDS,
        enabled: bool = settings.TRAVEL_CONTEXT_ENABLED,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled

    async def get_trip_context(self, preferences: GenerationPreferences) -> Optional[TravelContext]:
        if not self.enabled:
            return None

        payload = {
            "destination": preferences.destination,
            "startDate": preferences.startDate.isoformat(),
            "endDate": preferences.endDate.isoformat(),
            "vibe": preferences.vibe,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/trip-context", json=payload)
                response.raise_for_status()
                return TravelContext.model_validate(response.json())
        except Exception as error:
            logger.warning(
                "Travel context lookup failed destination=%s error=%s",
                preferences.destination,
                error,
            )
            return None
