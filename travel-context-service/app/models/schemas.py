from __future__ import annotations

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Coordinates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class GeocodedLocation(BaseModel):
    name: str
    displayName: Optional[str] = None
    countryCode: Optional[str] = None
    coordinates: Coordinates


class TripContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=1, max_length=200)
    startDate: datetime.date
    endDate: datetime.date
    vibe: str = Field(min_length=1, max_length=500)
    includeEvents: bool = True

    @model_validator(mode="after")
    def validate_date_range(self) -> "TripContextRequest":
        if self.endDate < self.startDate:
            raise ValueError("endDate must be on or after startDate")
        if (self.endDate - self.startDate).days >= 7:
            raise ValueError("trip length must not exceed 7 days")
        return self


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
    score: float = Field(default=0.0, ge=0)

    @field_validator("link", "thumbnail")
    @classmethod
    def validate_optional_link(cls, value: Optional[str]) -> Optional[str]:
        return _http_url(value) if value is not None else None


TimeBlock = Literal["MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]


class WeatherBlock(BaseModel):
    """Aggregated weather for one activity time block of a day."""

    timeBlock: TimeBlock
    condition: str
    temperatureC: Optional[float] = None
    precipitationMm: float = Field(default=0.0, ge=0)


class WeatherDaily(BaseModel):
    """Per-day weather, broken down into activity time blocks."""

    date: datetime.date
    source: Literal["forecast", "historical"]
    referenceDate: Optional[datetime.date] = None
    summary: str
    tempMinC: Optional[float] = None
    tempMaxC: Optional[float] = None
    precipitationProbabilityMax: Optional[int] = Field(default=None, ge=0, le=100)
    blocks: list[WeatherBlock] = Field(default_factory=list)


class TripContextResponse(BaseModel):
    destination: str
    coordinates: Coordinates
    events: list[EventCandidate] = Field(default_factory=list)
    weather: list[WeatherDaily] = Field(default_factory=list)


def _http_url(value: str) -> str:
    if not value.startswith(("http://", "https://")):
        raise ValueError("URL must use http or https")
    return value
