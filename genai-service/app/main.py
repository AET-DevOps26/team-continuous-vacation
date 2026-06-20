import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import schedules
from app.config.settings import settings
from app.observability import configure_observability

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(levelname)s:%(name)s:trace_id=%(otelTraceID)s span_id=%(otelSpanID)s:%(message)s",
)

app = FastAPI(
    title="TripTailor — GenAI API",
    description="Internal AI generation engine. Consumed only by the App API. Not exposed to the frontend.",
    version="1.0.0",
)

configure_observability(app, "genai-service")

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


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "genai-service"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "GenAI Service", "version": "1.0.0", "status": "running"}
