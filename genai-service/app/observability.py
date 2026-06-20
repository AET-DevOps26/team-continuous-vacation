import logging
import os
import re

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_configured = False
_log_record_factory_configured = False
_SECRET_QUERY_PARAM_RE = re.compile(r"(?i)(api_key=)[^&\s\"']+")


def configure_observability(app: FastAPI, service_name: str) -> None:
    """Configure OpenTelemetry tracing and log correlation for this service."""
    global _configured

    _install_log_record_defaults()

    if _is_truthy(os.getenv("OTEL_SDK_DISABLED")):
        LoggingInstrumentor().instrument(set_logging_format=False)
        return

    if not _configured:
        provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: service_name})
        )
        for exporter in _configured_exporters():
            provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        HTTPXClientInstrumentor().instrument()
        LoggingInstrumentor().instrument(set_logging_format=False)
        _configured = True

    FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str):
    return trace.get_tracer(name)


def _configured_exporters():
    exporters = {
        exporter.strip().lower()
        for exporter in os.getenv("OTEL_TRACES_EXPORTER", "none").split(",")
        if exporter.strip()
    }

    if "none" in exporters:
        return []

    configured = []
    if "otlp" in exporters:
        configured.append(OTLPSpanExporter(endpoint=_otlp_traces_endpoint()))
    if "console" in exporters:
        configured.append(ConsoleSpanExporter())
    return configured


def _otlp_traces_endpoint() -> str:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    if not endpoint:
        return "http://localhost:4318/v1/traces"
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/v1/traces"):
        return endpoint
    return f"{endpoint}/v1/traces"


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _install_log_record_defaults() -> None:
    """Ensure third-party logs can use the trace-aware log format."""
    global _log_record_factory_configured

    if _log_record_factory_configured:
        return

    original_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = original_factory(*args, **kwargs)
        message = record.getMessage()
        redacted_message = _SECRET_QUERY_PARAM_RE.sub(r"\1<redacted>", message)
        if redacted_message != message:
            record.msg = redacted_message
            record.args = ()
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            record.otelTraceID = format(span_context.trace_id, "032x")
            record.otelSpanID = format(span_context.span_id, "016x")
        else:
            record.otelTraceID = getattr(record, "otelTraceID", "-") or "-"
            record.otelSpanID = getattr(record, "otelSpanID", "-") or "-"
        return record

    logging.setLogRecordFactory(record_factory)
    _log_record_factory_configured = True
