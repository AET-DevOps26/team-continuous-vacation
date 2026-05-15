"""
Generated from OpenAPI specification: gen-ai.yaml
Pydantic models for the GenAI Service API
"""

from __future__ import annotations
from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    dayId: UUID
    timeBlock: TimeBlock
    title: str
    description: str
    durationMinutes: int
    isIndoor: Optional[bool] = None
    tags: Optional[List[ActivityTag]] = None


class Day(BaseModel):
    """Daily schedule with activities"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    dayNumber: int
    date: date
    activities: List[Activity]


class Schedule(BaseModel):
    """Complete schedule with multiple days"""
    days: List[Day]


class GenerationPreferences(BaseModel):
    """Preferences for generating a new schedule"""
    destination: str
    startDate: date
    endDate: date
    vibe: str


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
    instruction: str
    activity: Activity
    tripContext: TripContext
