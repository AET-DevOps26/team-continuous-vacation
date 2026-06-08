import json
import logging
from dataclasses import dataclass
from typing import Literal

from app.models.schemas import GenerationPreferences
from app.services.llm.base import LLMGenerationOptions, LLMProvider

logger = logging.getLogger(__name__)

DecisionSource = Literal["rules", "ai", "fallback"]

CITY_PLACE_KEYWORDS = {
    "architecture",
    "art",
    "arts",
    "castle",
    "cathedral",
    "church",
    "city",
    "culture",
    "cultural",
    "food",
    "gallery",
    "historic",
    "history",
    "landmark",
    "landmarks",
    "market",
    "museum",
    "museums",
    "old town",
    "park",
    "parks",
    "sightseeing",
    "sights",
    "shopping",
    "sporty",
    "theatre",
    "zoo",
}

NON_CITY_PLACE_KEYWORDS = {
    "all inclusive",
    "beach",
    "beaches",
    "beach vacation",
    "pool",
    "resort",
    "seaside",
    "ski",
    "skiing",
    "snowboard",
    "spa",
    "sunbathing",
    "wellness",
}


@dataclass(frozen=True)
class ContextDecision:
    should_fetch_events_context: bool
    source: DecisionSource
    reason: str

    @property
    def should_fetch_city_places(self) -> bool:
        return self.should_fetch_events_context


class ContextRelevanceClassifier:
    """Decides whether external events context is useful for a trip request."""

    async def should_fetch_events_context(
        self,
        preferences: GenerationPreferences,
        llm_provider: LLMProvider,
    ) -> ContextDecision:
        rule_decision = self._rule_decision(preferences)
        if rule_decision is not None:
            return rule_decision

        return await self._ai_decision(preferences, llm_provider)

    async def should_fetch_city_places(
        self,
        preferences: GenerationPreferences,
        llm_provider: LLMProvider,
    ) -> ContextDecision:
        return await self.should_fetch_events_context(preferences, llm_provider)

    def _rule_decision(self, preferences: GenerationPreferences) -> ContextDecision | None:
        text = f"{preferences.destination} {preferences.vibe}".lower()
        has_city_signal = any(keyword in text for keyword in CITY_PLACE_KEYWORDS)
        has_non_city_signal = any(keyword in text for keyword in NON_CITY_PLACE_KEYWORDS)

        if has_city_signal:
            return ContextDecision(
                should_fetch_events_context=True,
                source="rules",
                reason="Request contains city, culture, landmark, food, sport, or sightseeing signals where events may help.",
            )

        if has_non_city_signal:
            return ContextDecision(
                should_fetch_events_context=False,
                source="rules",
                reason=(
                    "Request contains beach, resort, ski, spa, or wellness signals "
                    "without concrete destination-event signals."
                ),
            )

        return None

    async def _ai_decision(
        self,
        preferences: GenerationPreferences,
        llm_provider: LLMProvider,
    ) -> ContextDecision:
        prompt = _classification_prompt(preferences)
        try:
            response = await llm_provider.generate(
                prompt=prompt,
                options=LLMGenerationOptions(
                    temperature=0.0,
                    max_tokens=300,
                    system_prompt="Return JSON only.",
                    json_mode=True,
                ),
            )
            parsed = _load_json(response)
            should_fetch = bool(parsed.get("shouldFetchEventsContext", parsed.get("shouldFetchCityPlaces", True)))
            reason = str(parsed.get("reason", "AI classified context relevance."))
            logger.info(
                "AI context relevance decision destination=%s should_fetch_events_context=%s reason=%s",
                preferences.destination,
                should_fetch,
                reason,
            )
            return ContextDecision(
                should_fetch_events_context=should_fetch,
                source="ai",
                reason=reason,
            )
        except Exception as error:
            logger.warning(
                "AI context relevance classification failed destination=%s error=%s; defaulting to events context",
                preferences.destination,
                error,
            )
            return ContextDecision(
                should_fetch_events_context=True,
                source="fallback",
                reason="Classifier failed; defaulting to events context.",
            )


def _classification_prompt(preferences: GenerationPreferences) -> str:
    request = {
        "destination": preferences.destination,
        "startDate": preferences.startDate.isoformat(),
        "endDate": preferences.endDate.isoformat(),
        "vibe": preferences.vibe,
    }
    return f"""
Classify whether real events context is useful for this trip request.

Events context means real dated events from external event listings for a concrete destination.

Trip request:
{json.dumps(request, indent=2, sort_keys=True)}

Return JSON only:
{{
  "shouldFetchCityPlaces": true,
  "shouldFetchEventsContext": true,
  "reason": "short reason"
}}

Guidance:
- Return true when the destination is a concrete city, region, or place where
  dated local events may improve the itinerary.
- Return true for city trips, culture, nightlife, food, shopping, sports,
  concerts, festivals, and mixed beach+culture requests.
- Return false for pure beach, resort, pool, ski, spa, wellness, or all-inclusive trips where local events are not useful.
- If uncertain, return true.
""".strip()


def _load_json(response_text: str) -> dict:
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    return json.loads(cleaned)
