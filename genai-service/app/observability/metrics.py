"""
Custom GenAI metrics.

These go beyond the auto-instrumented HTTP request count / latency / error rate
to give insight into the AI-specific behaviour of the service. They register
against the default prometheus_client registry, so they are exported on the same
/metrics endpoint set up by prometheus-fastapi-instrumentator.
"""

from prometheus_client import Counter, Histogram

# Number of LLM-backed generations, split by kind (schedule vs alternative
# activity) and outcome (success vs error). Lets us track GenAI throughput and
# failure rate independently of the HTTP layer.
GENERATIONS_TOTAL = Counter(
    "genai_generations_total",
    "Total LLM generations performed by the GenAI service.",
    labelnames=("kind", "outcome"),
)

# Wall-clock duration of a single LLM provider call. The dominant cost of every
# request, so its latency distribution is the key performance signal.
LLM_REQUEST_DURATION_SECONDS = Histogram(
    "genai_llm_request_duration_seconds",
    "Duration of a single LLM provider call in seconds.",
)
