"""
Generated from OpenAPI specification: gen-ai.yaml
Pydantic models for the GenAI Service API
"""

from __future__ import annotations
from datetime import date
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TimeBlock(str, Enum):
    """Time block enumeration for activities"""

    MORNING = "MORNING"
    NOON = "NOON"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"


class ActivityTag(str, Enum):
    """Activity tag enumeration"""

    OUTDOOR = "OUTDOOR"
    INDOOR = "INDOOR"
    CULTURAL = "CULTURAL"
    SPORTY = "SPORTY"
    RELAXING = "RELAXING"
    ADVENTUROUS = "ADVENTUROUS"
    FOOD = "FOOD"
    SHOPPING = "SHOPPING"
    ENTERTAINMENT = "ENTERTAINMENT"
    FAMILY_FRIENDLY = "FAMILY_FRIENDLY"
    PARTY = "PARTY"


class ActivityFields(BaseModel):
    """Shared activity fields for API and LLM-facing models."""

    timeBlock: TimeBlock
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    durationMinutes: int = Field(ge=30, le=360)
    isIndoor: Optional[bool] = None
    tags: Optional[List[ActivityTag]] = None


class GeneratedActivity(ActivityFields):
    """Activity shape expected from the LLM before IDs are assigned."""

    model_config = ConfigDict(extra="forbid")

    tags: List[ActivityTag] = Field(default_factory=list)


class Activity(GeneratedActivity):
    """Activity within a schedule."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dayId: UUID


class DayFields(BaseModel):
    """Shared day fields for API and LLM-facing models."""

    dayNumber: int = Field(ge=1)
    date: date


class GeneratedDay(DayFields):
    """Day shape expected from the LLM before IDs are assigned."""

    model_config = ConfigDict(extra="forbid")

    activities: List[GeneratedActivity] = Field(min_length=1)


class Day(DayFields):
    """Daily schedule with activities."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    activities: List[Activity]


class GeneratedSchedule(BaseModel):
    """Schedule shape expected from the LLM before IDs are assigned."""

    model_config = ConfigDict(extra="forbid")

    days: List[GeneratedDay] = Field(min_length=1)


class Schedule(BaseModel):
    """Complete schedule with multiple days."""

    days: List[Day]


class GenerationPreferences(BaseModel):
    """Preferences for generating a new schedule"""

    model_config = ConfigDict(extra="forbid")

    destination: str = Field(min_length=1, max_length=200)
    startDate: date
    endDate: date
    vibe: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_date_range(self) -> "GenerationPreferences":
        if self.endDate < self.startDate:
            raise ValueError("endDate must be on or after startDate")
        if (self.endDate - self.startDate).days >= 7:
            raise ValueError("trip length must not exceed 7 days")
        return self


class TripContext(BaseModel):
    """Complete trip context provided to the model"""

    model_config = ConfigDict(from_attributes=True)

    destination: str
    startDate: date
    endDate: date
    vibe: str
    days: List[Day]


class AlternativeActivityRequest(BaseModel):
    """Request for suggesting an alternative activity"""

    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(min_length=1, max_length=1000)
    activity: Activity
    tripContext: TripContext

    @model_validator(mode="after")
    def validate_activity_context(self) -> "AlternativeActivityRequest":
        matching = [
            candidate
            for day in self.tripContext.days
            for candidate in day.activities
            if candidate.id == self.activity.id
        ]
        if len(matching) != 1 or matching[0] != self.activity:
            raise ValueError("activity must occur exactly once in tripContext")
        parent = next(
            day
            for day in self.tripContext.days
            if any(candidate.id == self.activity.id for candidate in day.activities)
        )
        if self.activity.dayId != parent.id:
            raise ValueError("activity dayId must match its parent day")
        return self
