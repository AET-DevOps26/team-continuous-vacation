import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.propagate import inject

from app.observability import configure_observability


@pytest.mark.asyncio
async def test_trace_context_can_be_injected_after_observability_setup(monkeypatch):
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
    configure_observability(FastAPI(), "genai-service-test")

    carrier: dict[str, str] = {}
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-parent"):
        inject(carrier)

    traceparent = carrier.get("traceparent")
    assert traceparent is not None
    assert traceparent.startswith("00-")
