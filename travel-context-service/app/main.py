import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import context
from app.config.settings import settings
from app.observability import configure_observability


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await context.close_travel_context_service()

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s:%(name)s:trace_id=%(otelTraceID)s span_id=%(otelSpanID)s:%(message)s",
)

app = FastAPI(
    title="TripTailor — Travel Context API",
    description="Internal enrichment service for geocoding, events, and weather context.",
    version="1.0.0",
    lifespan=lifespan,
)

configure_observability(app, "travel-context-service")

app.include_router(context.router)

# Expose request count, latency, and error-rate metrics at GET /metrics.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "travel-context-service"}


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Configuration readiness without depending on public provider uptime."""
    return {"status": "ready", "service": "travel-context-service"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Travel Context Service",
        "version": "1.0.0",
        "status": "running",
    }
