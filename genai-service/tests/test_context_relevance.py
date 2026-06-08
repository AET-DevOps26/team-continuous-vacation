import pytest

from app.models.schemas import GenerationPreferences
from app.services.context_relevance import ContextRelevanceClassifier


class ClassifierLLMProvider:
    def __init__(self, response='{"shouldFetchEventsContext": false, "reason": "Pure beach trip."}'):
        self.response = response
        self.calls = 0

    async def generate(self, prompt, options):
        self.calls += 1
        return self.response


def preferences(destination="Mallorca", vibe="beach vacation"):
    return GenerationPreferences(
        destination=destination,
        startDate="2026-06-01",
        endDate="2026-06-04",
        vibe=vibe,
    )


@pytest.mark.asyncio
async def test_rules_skip_pure_beach_context_without_llm_call():
    llm = ClassifierLLMProvider()
    classifier = ContextRelevanceClassifier()

    decision = await classifier.should_fetch_events_context(preferences(), llm)

    assert decision.should_fetch_events_context is False
    assert decision.source == "rules"
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_rules_fetch_events_context_for_mixed_beach_and_culture():
    llm = ClassifierLLMProvider()
    classifier = ContextRelevanceClassifier()

    decision = await classifier.should_fetch_events_context(preferences("Barcelona", "beach and culture"), llm)

    assert decision.should_fetch_events_context is True
    assert decision.source == "rules"
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_ai_classifier_used_for_ambiguous_prompt():
    llm = ClassifierLLMProvider('{"shouldFetchEventsContext": true, "reason": "Destination has useful local events."}')
    classifier = ContextRelevanceClassifier()

    decision = await classifier.should_fetch_events_context(preferences("Lisbon", "surprise me"), llm)

    assert decision.should_fetch_events_context is True
    assert decision.source == "ai"
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_ai_classifier_failure_defaults_to_fetching_events_context():
    llm = ClassifierLLMProvider("not-json")
    classifier = ContextRelevanceClassifier()

    decision = await classifier.should_fetch_events_context(preferences("Lisbon", "surprise me"), llm)

    assert decision.should_fetch_events_context is True
    assert decision.source == "fallback"
