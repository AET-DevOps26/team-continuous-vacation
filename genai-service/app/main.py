from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import itinerary
from app.config.settings import settings

app = FastAPI(
    title="GenAI Service",
    description="AI-powered itinerary generation service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "genai-service"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GenAI Service",
        "version": "1.0.0",
        "status": "running"
    }
