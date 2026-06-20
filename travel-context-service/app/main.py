import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import context
from app.config.settings import settings
from app.observability import configure_observability

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s:%(name)s:trace_id=%(otelTraceID)s span_id=%(otelSpanID)s:%(message)s",
)

app = FastAPI(
    title="TripTailor — Travel Context API",
    description="Internal enrichment service for real-world places, events, weather, and routing context.",
    version="1.0.0",
)

configure_observability(app, "travel-context-service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(context.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "travel-context-service"}


@app.get("/")
async def root():
    return {
        "service": "Travel Context Service",
        "version": "1.0.0",
        "status": "running",
    }
