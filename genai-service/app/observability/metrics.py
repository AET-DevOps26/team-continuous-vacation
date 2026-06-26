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

# Requested completion-token budget per LLM call. This measures the configured
# request ceiling, not the number of tokens the provider actually consumed.
LLM_REQUESTED_TOKENS = Histogram(
    "genai_llm_requested_tokens",
    "Requested completion-token budget for a single LLM provider call.",
    labelnames=("provider", "model"),
    buckets=(100, 300, 500, 1000, 2000, 4000, 8000, 16000, 32000),
)

LLM_REQUESTED_TOKENS_TOTAL = Counter(
    "genai_llm_requested_completion_tokens_total",
    "Total requested completion-token budget across LLM provider calls.",
    labelnames=("provider", "model"),
)

# Actual provider-reported usage, when the provider returns usage metadata.
LLM_USAGE_TOKENS_TOTAL = Counter(
    "genai_llm_usage_tokens_total",
    "Provider-reported LLM token usage split by prompt, completion, and total.",
    labelnames=("provider", "model", "token_type"),
)
