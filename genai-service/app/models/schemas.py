"""
Generated from OpenAPI specification: gen-ai.yaml
Pydantic models for the GenAI Service API
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from enum import Enum
from uuid import UUID


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
    FAMILY_FRIENDLY = "FAMILY_FRIENDLY"
    PARTY = "PARTY"


class Activity(BaseModel):
    """Activity within a schedule"""
    id: UUID = Field(..., description="Unique identifier for the activity")
    dayId: UUID = Field(..., description="Reference to the parent day")
    timeBlock: TimeBlock = Field(..., description="Time block for the activity")
    title: str = Field(..., description="Activity title", example="Walking tour of the English Garden")
    description: str = Field(
        ..., 
        description="Activity description", 
        example="Explore the vast parklands and enjoy a beer at the Chinese Tower."
    )
    durationMinutes: int = Field(..., description="Duration in minutes", example=120)
    isIndoor: Optional[bool] = Field(None, description="Whether the activity is indoor", example=False)
    tags: Optional[List[ActivityTag]] = Field(
        default=None, 
        description="Activity tags", 
        example=["OUTDOOR", "CULTURAL"]
    )


class Day(BaseModel):
    """Daily schedule with activities"""
    id: UUID = Field(..., description="Unique identifier for the day")
    dayNumber: int = Field(..., description="Day number in the trip", example=1)
    date: date = Field(..., description="Date of the day", example="2026-05-15")
    activities: List[Activity] = Field(..., description="List of activities for this day")


class Schedule(BaseModel):
    """Complete schedule with multiple days"""
    days: List[Day] = Field(..., description="List of days in the schedule")


class GenerationPreferences(BaseModel):
    """Preferences for generating a new schedule"""
    destination: str = Field(..., description="Destination location", example="Munich")
    startDate: date = Field(..., description="Trip start date", example="2026-05-15")
    endDate: date = Field(..., description="Trip end date", example="2026-05-18")
    vibe: str = Field(..., description="Trip vibe/theme", example="Sporty and active")


class TripContext(BaseModel):
    """
    Complete trip context provided to the model.
    A trimmed view of the trip supplied as context to the model.
    Mirrors the App API Trip schema minus internal IDs that are
    irrelevant to generation quality.
    """
    destination: str = Field(..., description="Destination location", example="Munich")
    startDate: date = Field(..., description="Trip start date", example="2026-05-15")
    endDate: date = Field(..., description="Trip end date", example="2026-05-18")
    vibe: str = Field(..., description="Trip vibe/theme", example="Sporty and active")
    days: List[Day] = Field(..., description="All days in the trip with their activities")


class AlternativeActivityRequest(BaseModel):
    """Request for suggesting an alternative activity"""
    instruction: str = Field(
        ..., 
        description="Free-text directive describing what should change",
        example="Make this an indoor activity"
    )
    activity: Activity = Field(..., description="The activity that must be replaced")
    tripContext: TripContext = Field(
        ..., 
        description="The complete trip (all days and all activities) as currently persisted"
    )
