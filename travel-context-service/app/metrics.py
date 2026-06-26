"""
Custom Travel Context metrics.

These metrics complement the auto-instrumented FastAPI request metrics with
provider, cache, and response-shape signals for the context enrichment flow.
"""

from prometheus_client import Counter, Histogram

PROVIDER_REQUESTS_TOTAL = Counter(
    "travel_context_provider_requests_total",
    "External provider calls made by the Travel Context service.",
    labelnames=("provider", "outcome"),
)

PROVIDER_DURATION_SECONDS = Histogram(
    "travel_context_provider_duration_seconds",
    "Duration of external provider calls made by the Travel Context service.",
    labelnames=("provider",),
)

CACHE_REQUESTS_TOTAL = Counter(
    "travel_context_cache_requests_total",
    "Travel Context cache lookups split by cache and result.",
    labelnames=("cache", "result"),
)

EVENTS_RETURNED = Histogram(
    "travel_context_events_returned",
    "Number of event candidates returned in a trip context response.",
    buckets=(0, 1, 2, 5, 10, 20, 50),
)

WEATHER_DAYS_RETURNED = Histogram(
    "travel_context_weather_days_returned",
    "Number of weather days returned in a trip context response.",
    buckets=(0, 1, 2, 3, 5, 7, 10, 14, 21),
)
