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


def get_schedule_generation_prompt(preferences: GenerationPreferences) -> str:
    """Build the prompt used to generate a complete trip schedule."""
    expected_dates = _inclusive_dates(preferences)

    request_context = {
        "destination": preferences.destination,
        "startDate": preferences.startDate.isoformat(),
        "endDate": preferences.endDate.isoformat(),
        "vibe": preferences.vibe,
        "expectedDates": [date.isoformat() for date in expected_dates],
    }

    return f"""
Create a complete travel schedule for the trip request below.

Trip request:
{_json(request_context)}

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
