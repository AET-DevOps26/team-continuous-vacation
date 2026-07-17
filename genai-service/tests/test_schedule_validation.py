from datetime import date
import copy
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    Activity,
    ActivityTag,
    AlternativeActivityRequest,
    Day,
    GenerationPreferences,
    GeneratedSchedule,
    TimeBlock,
    TripContext,
)
from app.services.context_relevance import ContextDecision
from app.services.llm.base import LLMProviderError
from app.services.schedule_service import ScheduleGenerationError, ScheduleService


class StaticLLMProvider:
    def __init__(self, response):
        self.response = response

    async def generate(self, prompt, options):
        return self.response


class FailingLLMProvider:
    async def generate(self, prompt, options):
        raise LLMProviderError("rate limit")


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


def valid_schedule_payload():
    return {
        "days": [
            {
                "dayNumber": 1,
                "date": "2026-07-01",
                "activities": [
                    {
                        "timeBlock": "MORNING",
                        "title": "Morning museum",
                        "description": "Visit a museum.",
                        "durationMinutes": 90,
                        "isIndoor": True,
                        "tags": ["CULTURAL"],
                    },
                    {
                        "timeBlock": "AFTERNOON",
                        "title": "Afternoon park",
                        "description": "Walk through a park.",
                        "durationMinutes": 90,
                        "isIndoor": False,
                        "tags": ["OUTDOOR"],
                    },
                    {
                        "timeBlock": "EVENING",
                        "title": "Evening dinner",
                        "description": "Eat local food.",
                        "durationMinutes": 90,
                        "isIndoor": True,
                        "tags": ["FOOD"],
                    },
                ],
            }
        ]
    }


def validate_payload(payload):
    service = ScheduleService(
        llm_provider=StaticLLMProvider("{}"),
        travel_context_client=NullTravelContextClient(),
        context_relevance_classifier=AlwaysFetchContextClassifier(),
    )
    service._validate_schedule_contract(
        GeneratedSchedule.model_validate(payload), preferences()
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda payload: payload["days"].append(
                copy.deepcopy(payload["days"][0])
            ),
            "exactly one day",
        ),
        (lambda payload: payload["days"][0].update(dayNumber=2), "sequential"),
        (lambda payload: payload["days"][0].update(date="2026-07-02"), "dates"),
        (
            lambda payload: payload["days"][0].update(
                activities=payload["days"][0]["activities"][:2]
            ),
            "3 to 5",
        ),
        (
            lambda payload: payload["days"][0]["activities"][1].update(
                timeBlock="MORNING"
            ),
            "time block",
        ),
        (
            lambda payload: payload["days"][0]["activities"][1].update(
                title="  MORNING MUSEUM "
            ),
            "unique",
        ),
    ],
)
def test_schedule_contract_rejects_invariant_violations(mutation, message):
    payload = copy.deepcopy(valid_schedule_payload())
    mutation(payload)

    with pytest.raises(ValueError, match=message):
        validate_payload(payload)


def test_generated_schedule_rejects_extra_fields():
    payload = valid_schedule_payload()
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="extra_forbidden"):
        GeneratedSchedule.model_validate(payload)


def test_json_cleanup_and_tag_sanitizing_are_bounded():
    service = ScheduleService(
        llm_provider=StaticLLMProvider("{}"),
        travel_context_client=NullTravelContextClient(),
        context_relevance_classifier=AlwaysFetchContextClassifier(),
    )

    assert service._load_json("```json\n{\"days\": []}\n```", "schedule") == {
        "days": []
    }
    with pytest.raises(ValueError, match="empty"):
        service._load_json("   ", "schedule")

    activity = {"tags": [" cultural ", "CULTURAL", "not-supported", 42]}
    service._sanitize_activity_tags(activity, "test")
    assert activity["tags"] == ["CULTURAL"]

    non_list = {"tags": "CULTURAL"}
    service._sanitize_activity_tags(non_list, "test")
    assert non_list["tags"] == []


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


@pytest.mark.asyncio
async def test_alternative_generation_uses_fallback_when_llm_call_fails():
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
    request = AlternativeActivityRequest(
        instruction="Make this indoor and cultural",
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
                    activities=[replaced_activity],
                )
            ],
        ),
    )
    service = ScheduleService(
        llm_provider=FailingLLMProvider(),
        travel_context_client=NullTravelContextClient(),
        context_relevance_classifier=AlwaysFetchContextClassifier(),
    )

    alternative = await service.suggest_alternative(request)

    assert alternative.dayId == day_id
    assert alternative.timeBlock == TimeBlock.MORNING
    assert alternative.durationMinutes == 120
    assert alternative.title != replaced_activity.title
    assert alternative.isIndoor is True
    assert ActivityTag.INDOOR in alternative.tags
    assert ActivityTag.CULTURAL in alternative.tags
