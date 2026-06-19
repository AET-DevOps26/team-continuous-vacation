import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import schedules
from app.config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s:%(name)s:%(message)s",
)

app = FastAPI(
    title="TripTailor — GenAI API",
    description="Internal AI generation engine. Consumed only by the App API. Not exposed to the frontend.",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(schedules.router)

# Expose request count, latency, error-rate (and the custom GenAI metrics
# registered in app.observability.metrics) at GET /metrics.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "genai-service"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "GenAI Service", "version": "1.0.0", "status": "running"}
