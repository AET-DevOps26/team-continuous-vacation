from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.models.schemas import (
    GenerationPreferences,
    Schedule,
    AlternativeActivityRequest,
    Activity
)
from app.services.schedule_service import ScheduleService

app = FastAPI(
    title="TripTailor — GenAI API",
    description="Internal AI generation engine. Consumed only by the App API. Not exposed to the frontend.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

schedule_service = ScheduleService()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "genai-service"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GenAI Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/schedules", response_model=Schedule, tags=["Schedules"])
async def generate_schedule(preferences: GenerationPreferences):
    """Generate a full multi-day schedule"""
    try:
        schedule = await schedule_service.generate_schedule(preferences)
        return schedule
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")


@app.post("/activities/alternative", response_model=Activity, tags=["Activities"])
async def suggest_alternative_activity(request: AlternativeActivityRequest):
    """Suggest a replacement for a single activity"""
    try:
        alternative = await schedule_service.suggest_alternative(request)
        return alternative
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest alternative: {str(e)}")
