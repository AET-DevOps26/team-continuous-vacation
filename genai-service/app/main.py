import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import schedules
from app.config.settings import settings
from app.observability import configure_observability

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s:%(name)s:trace_id=%(otelTraceID)s span_id=%(otelSpanID)s:%(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await schedules.close_schedule_service()


app = FastAPI(
    title="TripTailor — GenAI API",
    description="Internal AI generation engine. Consumed only by the App API. Not exposed to the frontend.",
    version="1.0.0",
    lifespan=lifespan,
)

configure_observability(app, "genai-service")

# Include routers
app.include_router(schedules.router)

# Expose request count, latency, error-rate (and the custom GenAI metrics
# registered in app.observability.metrics) at GET /metrics.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "genai-service"}


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Configuration readiness without depending on external provider uptime."""
    return {
        "status": "ready",
        "service": "genai-service",
        "provider": settings.LLM_PROVIDER,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {"service": "GenAI Service", "version": "1.0.0", "status": "running"}
