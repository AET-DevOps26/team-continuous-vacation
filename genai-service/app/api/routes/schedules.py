"""
API routes matching the gen-ai.yaml OpenAPI specification
"""

from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import (
    GenerationPreferences,
    Schedule,
    AlternativeActivityRequest,
    Activity,
)
from app.services.schedule_service import ScheduleGenerationError, ScheduleService

router = APIRouter()


def get_schedule_service() -> ScheduleService:
    return ScheduleService()


@router.post("/schedules", response_model=Schedule, tags=["Schedules"])
async def generate_schedule(
    preferences: GenerationPreferences,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    """
    Generate a full multi-day schedule

    Args:
        preferences: GenerationPreferences with destination, dates, and vibe

    Returns:
        Schedule with complete daily activities
    """
    try:
        schedule = await schedule_service.generate_schedule(preferences)
        return schedule
    except ScheduleGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate schedule")


@router.post("/activities/alternative", response_model=Activity, tags=["Activities"])
async def suggest_alternative_activity(
    request: AlternativeActivityRequest,
    schedule_service: ScheduleService = Depends(get_schedule_service),
):
    """
    Suggest a replacement for a single activity

    Returns a single replacement activity that fits the given instruction.
    The full tripContext is provided so the model can see every activity
    already present in the trip and avoid generating a duplicate.
    The activity field identifies which activity is being replaced and
    must NOT appear in the output.

    Args:
        request: AlternativeActivityRequest with instruction, activity, and tripContext

    Returns:
        Activity: Proposed replacement activity
    """
    try:
        alternative = await schedule_service.suggest_alternative(request)
        return alternative
    except ScheduleGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Failed to suggest alternative activity"
        )
