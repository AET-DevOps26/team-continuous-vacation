from __future__ import annotations

import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float
    lon: float


class GeocodedLocation(BaseModel):
    name: str
    displayName: Optional[str] = None
    countryCode: Optional[str] = None
    coordinates: Coordinates


class TripContextRequest(BaseModel):
    destination: str = Field(min_length=1)
    startDate: datetime.date
    endDate: datetime.date
    vibe: str = Field(min_length=1)
    includeEvents: bool = True


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


TimeBlock = Literal["MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]


class WeatherBlock(BaseModel):
    """Aggregated weather for one activity time block of a day."""

    timeBlock: TimeBlock
    condition: str
    temperatureC: Optional[float] = None
    precipitationMm: float = 0.0


class WeatherDaily(BaseModel):
    """Per-day weather, broken down into activity time blocks."""

    date: datetime.date
    source: Literal["forecast", "historical"]
    referenceDate: Optional[datetime.date] = None
    summary: str
    tempMinC: Optional[float] = None
    tempMaxC: Optional[float] = None
    precipitationProbabilityMax: Optional[int] = None
    blocks: list[WeatherBlock] = Field(default_factory=list)


class TripContextResponse(BaseModel):
    destination: str
    coordinates: Coordinates
    events: list[EventCandidate] = Field(default_factory=list)
    places: list[PlaceCandidate] = Field(default_factory=list)
    weather: list[WeatherDaily] = Field(default_factory=list)
