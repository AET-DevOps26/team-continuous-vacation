"""
Prompt builders for schedule generation and activity regeneration.
"""

import json
from datetime import timedelta

from app.models.schemas import (
    ActivityTag,
    AlternativeActivityRequest,
    GenerationPreferences,
    TimeBlock,
)
from app.services.travel_context_client import TravelContext


def get_schedule_generation_prompt(
    preferences: GenerationPreferences,
    travel_context: TravelContext | None = None,
) -> str:
    """Build the prompt used to generate a complete trip schedule."""
    expected_dates = _inclusive_dates(preferences)

    request_context = {
        "destination": preferences.destination,
        "startDate": preferences.startDate.isoformat(),
        "endDate": preferences.endDate.isoformat(),
        "vibe": preferences.vibe,
        "expectedDates": [date.isoformat() for date in expected_dates],
    }
    real_events = _real_events_context(travel_context)
    weather = _weather_context(travel_context)

    return f"""
Create a complete travel schedule for the trip request below.

Trip request:
{_json(request_context)}

Real events available for this destination:
{_json(real_events)}

Weather outlook per day and time block (temperatureC in °C, precipitationMm in mm):
{_json(weather)}

Return JSON only. The response must match this exact shape:
{{
  "days": [
    {{
      "dayNumber": 1,
      "date": "YYYY-MM-DD",
      "activities": [
        {{
          "timeBlock": "MORNING",
          "title": "short specific activity title",
          "description": "one useful sentence explaining the plan",
          "durationMinutes": 90,
          "isIndoor": false,
          "tags": ["CULTURAL", "OUTDOOR"]
        }}
      ]
    }}
  ]
}}

Hard requirements:
- Generate exactly one day for each expected date, in the same order.
- Day numbers must start at 1 and increase by 1.
- Each day must contain 3 to 5 activities.
- Use each timeBlock at most once per day.
- Prefer MORNING, AFTERNOON, and EVENING for a compact day; add NOON or NIGHT only when it improves the itinerary.
- Activity titles must be unique across the whole trip.
- Activities must be realistic for the destination and strongly match the requested vibe.
- Use real events only when they fit the requested date range, destination, vibe, and day structure.
- Do not invent event ticket links, venues, exact times, source IDs, websites, or event dates.
- Generate normal attractions, landmarks, lakes, parks, and sightseeing ideas from your destination knowledge
  when they fit better than the available events.
- If event metadata does not say whether an activity is indoor/outdoor or cultural/sporty, infer reasonable activity fields.
- Use the weather outlook to plan each day. Match every activity to its own date and timeBlock weather entry.
- On time blocks with rain, drizzle, snow, thunderstorms, or high precipitation, prefer indoor or sheltered
  activities and set isIndoor to true; avoid hikes, long walks, and other exposed outdoor plans in those blocks.
- On clear, mainly clear, or partly cloudy time blocks, favor outdoor activities that match the vibe.
- Weather entries with "source": "historical" are seasonal estimates from last year, not a forecast; treat them as a
  general expectation and still avoid scheduling weather-sensitive outdoor activities on historically bad-weather blocks.
- When weather forces an indoor choice, keep the activity realistic and aligned with the requested vibe.
- Do not mention the weather data, forecasts, or temperatures in activity titles unless it is natural to the plan.
- Descriptions must be concrete enough for a traveler to understand what they will do.
- durationMinutes must be an integer from 30 to 360.
- isIndoor must be true for mostly indoor activities and false for mostly outdoor activities.
- tags must use only these values: {_enum_values(ActivityTag)}.
- timeBlock must use only these values: {_enum_values(TimeBlock)}.
- Do not include IDs, dayId values, markdown, comments, or fields not shown in the schema.
""".strip()


def get_alternative_activity_prompt(request: AlternativeActivityRequest) -> str:
    """Build the prompt used to generate one replacement activity."""
    context = {
        "instruction": request.instruction,
        "activityToReplace": request.activity.model_dump(mode="json"),
        "tripContext": request.tripContext.model_dump(mode="json"),
        "existingActivityTitlesToAvoid": [
            activity.title
            for day in request.tripContext.days
            for activity in day.activities
            if activity.id != request.activity.id
        ],
    }

    return f"""
Create one replacement activity for the trip context below.

Regeneration context:
{_json(context)}

Return JSON only. The response must match this exact shape:
{{
  "timeBlock": "{request.activity.timeBlock.value}",
  "title": "short specific replacement activity title",
  "description": "one useful sentence explaining the replacement",
  "durationMinutes": {request.activity.durationMinutes},
  "isIndoor": true,
  "tags": ["INDOOR", "CULTURAL"]
}}

Hard requirements:
- Generate a replacement activity, not a full schedule.
- Follow the user's instruction as the primary change request.
- Keep the replacement on the same trip day and in the same timeBlock unless the instruction makes that impossible.
- Do not reuse the current activity title.
- Do not duplicate any existing activity title from the trip context.
- Keep the activity realistic for the destination, date, vibe, and surrounding activities.
- durationMinutes must be an integer from 30 to 360 and should stay close to the replaced activity's duration.
- isIndoor must match the replacement activity.
- tags must use only these values: {_enum_values(ActivityTag)}.
- timeBlock must use only these values: {_enum_values(TimeBlock)}.
- Do not include IDs, dayId values, markdown, comments, or fields not shown in the schema.
""".strip()


def _inclusive_dates(preferences: GenerationPreferences):
    dates = []
    current_date = preferences.startDate
    while current_date <= preferences.endDate:
        dates.append(current_date)
        current_date += timedelta(days=1)
    return dates


def _enum_values(enum_type) -> str:
    return ", ".join(member.value for member in enum_type)


def _json(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _weather_context(travel_context: TravelContext | None):
    if travel_context is None:
        return []

    days = []
    for day in travel_context.weather:
        days.append(
            {
                "date": day.date,
                "source": day.source,
                "summary": day.summary,
                "tempMinC": day.tempMinC,
                "tempMaxC": day.tempMaxC,
                "precipitationProbabilityMax": day.precipitationProbabilityMax,
                "blocks": {
                    block.timeBlock: {
                        "condition": block.condition,
                        "temperatureC": block.temperatureC,
                        "precipitationMm": block.precipitationMm,
                    }
                    for block in day.blocks
                },
            }
        )
    return days


def _real_events_context(travel_context: TravelContext | None):
    if travel_context is None:
        return []

    events = []
    for event in travel_context.events[:10]:
        events.append(
            {
                "title": event.title,
                "description": event.description,
                "dateText": event.dateText,
                "startDate": event.startDate,
                "when": event.when,
                "venueName": event.venueName,
                "address": event.address,
                "link": event.link,
                "ticketLinks": [
                    {
                        "source": ticket.source,
                        "link": ticket.link,
                        "linkType": ticket.linkType,
                    }
                    for ticket in event.ticketLinks[:3]
                ],
                "score": event.score,
                "sourceId": event.sourceId,
            }
        )
    return events
