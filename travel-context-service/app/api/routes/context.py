from functools import lru_cache

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import TripContextRequest, TripContextResponse
from app.services.context_service import TravelContextService

router = APIRouter()
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_travel_context_service() -> TravelContextService:
    return TravelContextService()


async def close_travel_context_service() -> None:
    if get_travel_context_service.cache_info().currsize:
        await get_travel_context_service().aclose()
        get_travel_context_service.cache_clear()


@router.post("/trip-context", response_model=TripContextResponse, tags=["Travel Context"])
async def get_trip_context(
    request: TripContextRequest,
    service: TravelContextService = Depends(get_travel_context_service),
) -> TripContextResponse:
    try:
        return await service.build_trip_context(request)
    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Failed to build travel context")
        raise HTTPException(
            status_code=502, detail="Failed to build travel context"
        ) from error
