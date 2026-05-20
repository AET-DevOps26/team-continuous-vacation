from app.models.schemas import AlternativeActivityRequest, GenerationPreferences


TIME_BLOCKS = ["MORNING", "NOON", "AFTERNOON", "EVENING", "NIGHT"]
ACTIVITY_TAGS = [
    "OUTDOOR",
    "INDOOR",
    "CULTURAL",
    "SPORTY",
    "RELAXING",
    "ADVENTUROUS",
    "FOOD",
    "SHOPPING",
    "FAMILY_FRIENDLY",
    "PARTY",
]


def get_schedule_generation_prompt(preferences: GenerationPreferences) -> str:
    """
    Returns the prompt for schedule generation.
    """
    days_count = (preferences.endDate - preferences.startDate).days + 1
    return f"""Generate a travel itinerary as strict JSON only.

Trip data:
- destination: {preferences.destination}
- startDate: {preferences.startDate}
- endDate: {preferences.endDate}
- dayCount: {days_count}
- requested vibe: {preferences.vibe}

Requirements:
- Return exactly {days_count} days, one for every calendar date from {preferences.startDate} through {preferences.endDate}.
- Use dayNumber values starting at 1 and increasing by 1.
- Each day must contain 3 to 5 activities.
- Use each timeBlock at most once per day.
- Activities must be specific to {preferences.destination}, realistic for the date range, and aligned with the requested vibe.
- Avoid duplicate titles or near-duplicate concepts across the itinerary.
- durationMinutes must be a realistic positive integer between 30 and 360.
- Use only these timeBlock values: {", ".join(TIME_BLOCKS)}.
- Use only these tags: {", ".join(ACTIVITY_TAGS)}.
- Do not include ids or dayIds; the service assigns them.
- Return JSON only. Do not include markdown, comments, explanations, or trailing text.

JSON shape:
{{
  "days": [
    {{
      "dayNumber": 1,
      "date": "YYYY-MM-DD",
      "activities": [
        {{
          "timeBlock": "MORNING",
          "title": "string",
          "description": "string",
          "durationMinutes": 120,
          "isIndoor": boolean,
          "tags": ["CULTURAL", "OUTDOOR"]
        }}
      ]
    }}
  ]
}}
"""


def get_alternative_activity_prompt(request: AlternativeActivityRequest) -> str:
    """
    Returns the prompt for alternative activity suggestion.
    """
    trip_context_json = request.tripContext.model_dump_json()
    replaced_activity_json = request.activity.model_dump_json()

    return f"""Suggest one replacement activity as strict JSON only.

User instruction:
{request.instruction}

Activity to replace:
{replaced_activity_json}

Full trip context:
{trip_context_json}

Requirements:
- Replace the provided activity; do not return the same title or concept.
- Respect the user instruction first, then the trip vibe.
- Avoid duplicating any activity already present in tripContext.days.
- Keep the replacement suitable for the same destination and day.
- Prefer the same timeBlock and similar duration unless the instruction clearly requires a change.
- durationMinutes must be a realistic positive integer between 30 and 360.
- Use only these timeBlock values: {", ".join(TIME_BLOCKS)}.
- Use only these tags: {", ".join(ACTIVITY_TAGS)}.
- Do not include id or dayId; the service assigns them.
- Return JSON only. Do not include markdown, comments, explanations, or trailing text.

JSON shape:
{{
  "timeBlock": "MORNING",
  "title": "string",
  "description": "string",
  "durationMinutes": 120,
  "isIndoor": boolean,
  "tags": ["CULTURAL", "INDOOR"]
}}
"""
