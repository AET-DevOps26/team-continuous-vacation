"""
API routes matching the gen-ai.yaml OpenAPI specification
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    GenerationPreferences,
    Schedule,
    AlternativeActivityRequest,
    Activity
)
from app.services.schedule_service import ScheduleService

router = APIRouter()
schedule_service = ScheduleService()


@router.post("/schedules", response_model=Schedule, tags=["Schedules"])
async def generate_schedule(preferences: GenerationPreferences):
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
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate schedule: {str(e)}"
        )


@router.post("/activities/alternative", response_model=Activity, tags=["Activities"])
async def suggest_alternative_activity(request: AlternativeActivityRequest):
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to suggest alternative activity: {str(e)}"
        )
