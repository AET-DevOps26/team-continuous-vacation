from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import TripContextRequest, TripContextResponse
from app.services.context_service import TravelContextService

router = APIRouter()


def get_travel_context_service() -> TravelContextService:
    return TravelContextService()


@router.post("/trip-context", response_model=TripContextResponse, tags=["Travel Context"])
async def get_trip_context(
    request: TripContextRequest,
    service: TravelContextService = Depends(get_travel_context_service),
):
    try:
        return await service.build_trip_context(request)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Failed to build travel context: {error}") from error
