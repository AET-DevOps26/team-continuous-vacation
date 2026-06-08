"""
Service for AI-powered schedule generation based on OpenAPI specification
"""

import logging
import json
from datetime import timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.models.schemas import (
    Activity,
    ActivityTag,
    AlternativeActivityRequest,
    Day,
    GeneratedActivity,
    GeneratedDay,
    GeneratedSchedule,
    GenerationPreferences,
    Schedule,
)
from app.config.settings import settings
from app.services.llm.base import LLMGenerationOptions, LLMProvider
from app.services.llm.factory import LLMProviderFactory
from app.services.prompts.schedule_prompts import (
    get_alternative_activity_prompt,
    get_schedule_generation_prompt,
)
from app.services.context_relevance import ContextRelevanceClassifier
from app.services.travel_context_client import TravelContextClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You generate travel itinerary data for an internal API. "
    "Return valid JSON only, matching the requested schema exactly."
)


class ScheduleGenerationError(Exception):
    """Raised when schedule generation cannot produce a valid response."""


class ScheduleService:
    """Service for AI-powered schedule generation"""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        travel_context_client: Optional[TravelContextClient] = None,
        context_relevance_classifier: Optional[ContextRelevanceClassifier] = None,
    ):
        self.llm_provider = llm_provider or LLMProviderFactory.get_provider()
        self.travel_context_client = travel_context_client or TravelContextClient()
        self.context_relevance_classifier = context_relevance_classifier or ContextRelevanceClassifier()
        self.model_name = settings.MODEL_NAME
        self.temperature = settings.TEMPERATURE
        self.max_tokens = settings.MAX_TOKENS

    async def generate_schedule(self, preferences: GenerationPreferences) -> Schedule:
        """
        Generate a complete schedule using LLM

        Args:
            preferences: GenerationPreferences with destination, dates, and vibe

        Returns:
            Schedule with all days and activities
        """
        context_decision = await self.context_relevance_classifier.should_fetch_events_context(
            preferences,
            self.llm_provider,
        )
        logger.info(
            "Context relevance decision destination=%s should_fetch_events_context=%s source=%s reason=%s",
            preferences.destination,
            context_decision.should_fetch_events_context,
            context_decision.source,
            context_decision.reason,
        )
        # Weather is useful for every trip (even pure beach trips), so we always
        # fetch the travel context for it. Paid event lookups stay gated behind
        # the relevance decision via the includeEvents flag.
        travel_context = await self.travel_context_client.get_trip_context(
            preferences,
            include_events=context_decision.should_fetch_events_context,
        )
        prompt = get_schedule_generation_prompt(preferences, travel_context)
        logger.debug(
            "Starting schedule LLM generation destination=%s startDate=%s endDate=%s "
            "vibe=%s context_events=%s context_weather_days=%s prompt_length=%s prompt=%s",
            preferences.destination,
            preferences.startDate,
            preferences.endDate,
            preferences.vibe,
            len(travel_context.events) if travel_context else 0,
            len(travel_context.weather) if travel_context else 0,
            len(prompt),
            prompt,
        )
        response_text = await self._call_llm(prompt)
        logger.debug(
            "Schedule LLM raw response length=%s response=%r",
            len(response_text or ""),
            response_text,
        )

        try:
            parsed_json = self._load_json(response_text, "schedule")
            self._sanitize_schedule_tags(parsed_json)
            logger.debug("Schedule LLM parsed JSON: %s", parsed_json)
            parsed_schedule = GeneratedSchedule.model_validate(parsed_json)
            self._validate_schedule_contract(parsed_schedule, preferences)
            days = [self._to_day(day_data) for day_data in parsed_schedule.days]
            logger.info(
                "Generated schedule destination=%s days=%s activities=%s",
                preferences.destination,
                len(days),
                sum(len(day.activities) for day in days),
            )
            return Schedule(days=days)
        except (json.JSONDecodeError, KeyError, ValueError, ValidationError) as error:
            logger.warning(
                "Failed to parse schedule LLM response: %s raw_response=%r",
                error,
                response_text,
            )
            raise ScheduleGenerationError(
                "Generated schedule did not match the expected format"
            ) from error

    async def suggest_alternative(
        self, request: AlternativeActivityRequest
    ) -> Activity:
        """
        Suggest an alternative activity based on user instruction

        Args:
            request: AlternativeActivityRequest with instruction, activity, and context

        Returns:
            Activity: New alternative activity
        """
        prompt = get_alternative_activity_prompt(request)
        logger.debug(
            "Starting alternative activity LLM generation activity_id=%s title=%r "
            "instruction=%r prompt_length=%s prompt=%s",
            request.activity.id,
            request.activity.title,
            request.instruction,
            len(prompt),
            prompt,
        )
        response_text = await self._call_llm(prompt)
        logger.debug(
            "Alternative activity LLM raw response length=%s response=%r",
            len(response_text or ""),
            response_text,
        )

        try:
            parsed_json = self._load_json(response_text, "alternative activity")
            self._sanitize_activity_tags(parsed_json, "alternative activity")
            logger.debug("Alternative activity LLM parsed JSON: %s", parsed_json)
            activity_data = GeneratedActivity.model_validate(parsed_json)
            self._validate_alternative_contract(activity_data, request)
            activity = self._to_activity(activity_data, request.activity.dayId)
            logger.info(
                "Generated alternative activity original_id=%s new_id=%s title=%r",
                request.activity.id,
                activity.id,
                activity.title,
            )
            return activity
        except (json.JSONDecodeError, KeyError, ValueError, ValidationError) as error:
            logger.warning(
                "Failed to parse alternative activity LLM response: %s raw_response=%r",
                error,
                response_text,
            )
            raise ScheduleGenerationError(
                "Generated activity did not match the expected format"
            ) from error

    async def _call_llm(self, prompt: str) -> str:
        """
        Make API call to LLM
        """
        options = LLMGenerationOptions(
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
        )
        logger.debug(
            "Calling LLM provider=%s model=%s temperature=%s max_tokens=%s json_mode=%s "
            "system_prompt=%s",
            self.llm_provider.__class__.__name__,
            self.model_name,
            options.temperature,
            options.max_tokens,
            options.json_mode,
            options.system_prompt,
        )
        return await self.llm_provider.generate(
            prompt=prompt,
            options=options,
        )

    def _load_json(self, response_text: str, generation_name: str) -> dict:
        cleaned = response_text.strip()
        if not cleaned:
            raise ValueError(f"{generation_name} LLM response was empty")
        if cleaned.startswith("```json"):
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
        logger.debug(
            "Cleaned %s LLM response for JSON parse length=%s response=%r",
            generation_name,
            len(cleaned),
            cleaned,
        )
        return json.loads(cleaned)

    def _sanitize_schedule_tags(self, schedule_data: dict[str, Any]) -> None:
        days = schedule_data.get("days")
        if not isinstance(days, list):
            return

        for day_index, day in enumerate(days):
            if not isinstance(day, dict):
                continue

            activities = day.get("activities")
            if not isinstance(activities, list):
                continue

            for activity_index, activity in enumerate(activities):
                self._sanitize_activity_tags(
                    activity,
                    f"schedule day {day_index + 1} activity {activity_index + 1}",
                )

    def _sanitize_activity_tags(
        self,
        activity_data: Any,
        location: str,
    ) -> None:
        if not isinstance(activity_data, dict):
            return

        tags = activity_data.get("tags")
        if tags is None:
            activity_data["tags"] = []
            return
        if not isinstance(tags, list):
            logger.warning(
                "Dropping invalid LLM tags field at %s because it was not a list: %r",
                location,
                tags,
            )
            activity_data["tags"] = []
            return

        allowed_tags = {tag.value for tag in ActivityTag}
        sanitized_tags = []
        dropped_tags = []
        for raw_tag in tags:
            normalized_tag = self._normalize_tag_value(raw_tag)
            if normalized_tag in allowed_tags:
                if normalized_tag not in sanitized_tags:
                    sanitized_tags.append(normalized_tag)
            else:
                dropped_tags.append(raw_tag)

        if dropped_tags:
            logger.warning(
                "Dropping unsupported LLM activity tags at %s: %r",
                location,
                dropped_tags,
            )
        if sanitized_tags != tags:
            logger.debug(
                "Sanitized LLM activity tags at %s from %r to %r",
                location,
                tags,
                sanitized_tags,
            )
        activity_data["tags"] = sanitized_tags

    def _normalize_tag_value(self, raw_tag: Any) -> str:
        if not isinstance(raw_tag, str):
            return ""
        return raw_tag.strip().upper().replace("-", "_").replace(" ", "_")

    def _validate_schedule_contract(
        self,
        parsed_schedule: GeneratedSchedule,
        preferences: GenerationPreferences,
    ) -> None:
        expected_dates = []
        current_date = preferences.startDate
        while current_date <= preferences.endDate:
            expected_dates.append(current_date)
            current_date += timedelta(days=1)

        if len(parsed_schedule.days) != len(expected_dates):
            raise ValueError("Schedule must contain exactly one day per requested date")

        seen_titles = set()
        for index, day in enumerate(parsed_schedule.days):
            expected_day_number = index + 1
            if day.dayNumber != expected_day_number:
                raise ValueError("Schedule day numbers must be sequential")
            if day.date != expected_dates[index]:
                raise ValueError("Schedule dates must match the requested trip dates")
            if not 3 <= len(day.activities) <= 5:
                raise ValueError("Each day must contain 3 to 5 activities")

            seen_time_blocks = set()
            for activity in day.activities:
                if activity.timeBlock in seen_time_blocks:
                    raise ValueError("A time block can only appear once per day")
                seen_time_blocks.add(activity.timeBlock)

                normalized_title = activity.title.strip().lower()
                if normalized_title in seen_titles:
                    raise ValueError(
                        "Activity titles must be unique across the schedule"
                    )
                seen_titles.add(normalized_title)

    def _validate_alternative_contract(
        self,
        activity_data: GeneratedActivity,
        request: AlternativeActivityRequest,
    ) -> None:
        replacement_title = activity_data.title.strip().lower()
        original_title = request.activity.title.strip().lower()
        if replacement_title == original_title:
            raise ValueError("Alternative activity must not reuse the replaced title")

        existing_titles = {
            activity.title.strip().lower()
            for day in request.tripContext.days
            for activity in day.activities
            if activity.id != request.activity.id
        }
        if replacement_title in existing_titles:
            raise ValueError(
                "Alternative activity must not duplicate an existing activity"
            )

    def _to_day(self, day_data: GeneratedDay) -> Day:
        day_id = uuid4()
        return Day(
            id=day_id,
            dayNumber=day_data.dayNumber,
            date=day_data.date,
            activities=[
                self._to_activity(activity_data, day_id)
                for activity_data in day_data.activities
            ],
        )

    def _to_activity(
        self, activity_data: GeneratedActivity, day_id: UUID
    ) -> Activity:
        return Activity(
            id=uuid4(),
            dayId=day_id,
            timeBlock=activity_data.timeBlock,
            title=activity_data.title,
            description=activity_data.description,
            durationMinutes=activity_data.durationMinutes,
            isIndoor=activity_data.isIndoor,
            tags=activity_data.tags,
        )
