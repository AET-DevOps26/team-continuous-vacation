import pytest

from app.models.schemas import GenerationPreferences
from app.services.prompts.schedule_prompts import get_schedule_generation_prompt
from app.services.schedule_service import ScheduleService
from app.services.travel_context_client import (
    Coordinates,
    EventCandidate,
    TravelContext,
    WeatherBlock,
    WeatherDaily,
)


def _sample_weather():
    return [
        WeatherDaily(
            date="2026-06-01",
            source="forecast",
            summary="Light rain, 12-16°C",
            tempMinC=12.0,
            tempMaxC=16.0,
            precipitationProbabilityMax=70,
            blocks=[
                WeatherBlock(
                    timeBlock="MORNING",
                    condition="Light rain",
                    temperatureC=13.0,
                    precipitationMm=1.0,
                ),
                WeatherBlock(
                    timeBlock="AFTERNOON",
                    condition="Thunderstorm",
                    temperatureC=15.0,
                    precipitationMm=8.0,
                ),
            ],
        )
    ]


class CapturingLLMProvider:
    def __init__(self):
        self.prompt = None

    async def generate(self, prompt, options):
        self.prompt = prompt
        return """
        {
          "days": [
            {
              "dayNumber": 1,
              "date": "2026-06-01",
              "activities": [
                {
                  "timeBlock": "MORNING",
                  "title": "Marienplatz old town walk",
                  "description": "Explore the central square and nearby landmarks.",
                  "durationMinutes": 90,
                  "isIndoor": false,
                  "tags": ["CULTURAL", "OUTDOOR"]
                },
                {
                  "timeBlock": "AFTERNOON",
                  "title": "Englischer Garten stroll",
                  "description": "Walk through the famous park and river paths.",
                  "durationMinutes": 120,
                  "isIndoor": false,
                  "tags": ["RELAXING", "OUTDOOR"]
                },
                {
                  "timeBlock": "EVENING",
                  "title": "Schwabing dinner",
                  "description": "Finish with a casual local dinner.",
                  "durationMinutes": 90,
                  "isIndoor": true,
                  "tags": ["FOOD"]
                }
              ]
            }
          ]
        }
        """


class FakeTravelContextClient:
    def __init__(self):
        self.calls = 0
        self.last_include_events = None

    async def get_trip_context(self, preferences, include_events=True):
        self.calls += 1
        self.last_include_events = include_events
        events = (
            [
                EventCandidate(
                    sourceId="serpapi:1",
                    title="Munich Summer Festival",
                    venueName="Olympiapark",
                    dateText="Fri, Jun 5, 7:00 PM",
                    score=40,
                )
            ]
            if include_events
            else []
        )
        return TravelContext(
            destination=preferences.destination,
            coordinates=Coordinates(lat=48.137154, lon=11.576124),
            events=events,
            places=[],
            weather=_sample_weather(),
        )


def test_schedule_prompt_includes_real_events():
    preferences = GenerationPreferences(
        destination="Munich",
        startDate="2026-06-01",
        endDate="2026-06-01",
        vibe="cultural",
    )
    travel_context = TravelContext(
        destination="Munich",
        coordinates=Coordinates(lat=48.137154, lon=11.576124),
        events=[
            EventCandidate(
                sourceId="serpapi:1",
                title="Munich Summer Festival",
                venueName="Olympiapark",
                dateText="Fri, Jun 5, 7:00 PM",
                score=40,
            )
        ],
        places=[],
    )

    prompt = get_schedule_generation_prompt(preferences, travel_context)

    assert "Real events available for this destination" in prompt
    assert "Munich Summer Festival" in prompt
    assert "Ranked real places available for this destination" not in prompt
    assert "Prefer the ranked real places" not in prompt


def test_schedule_prompt_includes_per_block_weather():
    preferences = GenerationPreferences(
        destination="Munich",
        startDate="2026-06-01",
        endDate="2026-06-01",
        vibe="cultural",
    )
    travel_context = TravelContext(
        destination="Munich",
        coordinates=Coordinates(lat=48.137154, lon=11.576124),
        events=[],
        places=[],
        weather=_sample_weather(),
    )

    prompt = get_schedule_generation_prompt(preferences, travel_context)

    assert "Weather outlook per day and time block" in prompt
    assert "Thunderstorm" in prompt
    assert "AFTERNOON" in prompt
    assert "prefer indoor or sheltered" in prompt


@pytest.mark.asyncio
async def test_schedule_generation_uses_travel_context_client():
    llm_provider = CapturingLLMProvider()
    travel_context_client = FakeTravelContextClient()
    service = ScheduleService(
        llm_provider=llm_provider,
        travel_context_client=travel_context_client,
    )
    preferences = GenerationPreferences(
        destination="Munich",
        startDate="2026-06-01",
        endDate="2026-06-01",
        vibe="cultural",
    )

    await service.generate_schedule(preferences)

    assert llm_provider.prompt is not None
    assert "Munich Summer Festival" in llm_provider.prompt
    assert travel_context_client.calls == 1
    assert travel_context_client.last_include_events is True


@pytest.mark.asyncio
async def test_schedule_generation_skips_events_but_keeps_weather_for_pure_beach_vacation():
    llm_provider = CapturingLLMProvider()
    travel_context_client = FakeTravelContextClient()
    service = ScheduleService(
        llm_provider=llm_provider,
        travel_context_client=travel_context_client,
    )
    preferences = GenerationPreferences(
        destination="Mallorca",
        startDate="2026-06-01",
        endDate="2026-06-01",
        vibe="beach vacation",
    )

    await service.generate_schedule(preferences)

    assert llm_provider.prompt is not None
    # Paid event lookups stay gated for a pure beach trip ...
    assert "Munich Summer Festival" not in llm_provider.prompt
    assert travel_context_client.last_include_events is False
    # ... but the context is still fetched so weather can inform planning.
    assert travel_context_client.calls == 1
    assert "Light rain" in llm_provider.prompt
