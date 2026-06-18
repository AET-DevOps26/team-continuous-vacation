from datetime import date
from uuid import UUID

import pytest

from app.models.schemas import (
    Activity,
    ActivityTag,
    AlternativeActivityRequest,
    Day,
    GenerationPreferences,
    TimeBlock,
    TripContext,
)
from app.services.context_relevance import ContextDecision
from app.services.schedule_service import ScheduleGenerationError, ScheduleService


class StaticLLMProvider:
    def __init__(self, response):
        self.response = response

    async def generate(self, prompt, options):
        return self.response


class NullTravelContextClient:
    async def get_trip_context(self, preferences, include_events=True):
        return None


class AlwaysFetchContextClassifier:
    async def should_fetch_events_context(self, preferences, llm_provider):
        return ContextDecision(True, "rules", "test")


def preferences():
    return GenerationPreferences(
        destination="Munich",
        startDate=date(2026, 7, 1),
        endDate=date(2026, 7, 1),
        vibe="cultural",
    )


@pytest.mark.asyncio
async def test_schedule_generation_rejects_malformed_llm_json():
    service = ScheduleService(
        llm_provider=StaticLLMProvider("not-json"),
        travel_context_client=NullTravelContextClient(),
        context_relevance_classifier=AlwaysFetchContextClassifier(),
    )

    with pytest.raises(ScheduleGenerationError, match="expected format"):
        await service.generate_schedule(preferences())


@pytest.mark.asyncio
async def test_schedule_generation_rejects_partial_schedule_contract():
    service = ScheduleService(
        llm_provider=StaticLLMProvider(
            """
            {
              "days": [
                {
                  "dayNumber": 1,
                  "date": "2026-07-01",
                  "activities": [
                    {
                      "timeBlock": "MORNING",
                      "title": "Marienplatz",
                      "description": "Visit the central square.",
                      "durationMinutes": 90,
                      "isIndoor": false,
                      "tags": ["CULTURAL"]
                    }
                  ]
                }
              ]
            }
            """
        ),
        travel_context_client=NullTravelContextClient(),
        context_relevance_classifier=AlwaysFetchContextClassifier(),
    )

    with pytest.raises(ScheduleGenerationError, match="expected format"):
        await service.generate_schedule(preferences())


@pytest.mark.asyncio
async def test_alternative_generation_rejects_duplicate_existing_activity_title():
    day_id = UUID("550e8400-e29b-41d4-a716-446655440001")
    replaced_activity = Activity(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        dayId=day_id,
        timeBlock=TimeBlock.MORNING,
        title="Outdoor walking tour",
        description="Walk outside.",
        durationMinutes=120,
        isIndoor=False,
        tags=[ActivityTag.OUTDOOR],
    )
    existing_activity = Activity(
        id=UUID("550e8400-e29b-41d4-a716-446655440002"),
        dayId=day_id,
        timeBlock=TimeBlock.AFTERNOON,
        title="Deutsches Museum",
        description="Visit an indoor museum.",
        durationMinutes=120,
        isIndoor=True,
        tags=[ActivityTag.INDOOR, ActivityTag.CULTURAL],
    )
    request = AlternativeActivityRequest(
        instruction="Make this indoor",
        activity=replaced_activity,
        tripContext=TripContext(
            destination="Munich",
            startDate=date(2026, 7, 1),
            endDate=date(2026, 7, 1),
            vibe="cultural",
            days=[
                Day(
                    id=day_id,
                    dayNumber=1,
                    date=date(2026, 7, 1),
                    activities=[replaced_activity, existing_activity],
                )
            ],
        ),
    )
    service = ScheduleService(
        llm_provider=StaticLLMProvider(
            """
            {
              "timeBlock": "EVENING",
              "title": "Deutsches Museum",
              "description": "A duplicate title should be rejected.",
              "durationMinutes": 90,
              "isIndoor": true,
              "tags": ["INDOOR"]
            }
            """
        ),
        travel_context_client=NullTravelContextClient(),
        context_relevance_classifier=AlwaysFetchContextClassifier(),
    )

    with pytest.raises(ScheduleGenerationError, match="expected format"):
        await service.suggest_alternative(request)
