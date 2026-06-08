from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


SERVICE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=(SERVICE_DIR / ".env.example", SERVICE_DIR / ".env"),
        case_sensitive=True,
    )

    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    PHOTON_BASE_URL: str = "https://photon.komoot.io"
    OVERPASS_BASE_URL: str = "https://overpass-api.de/api/interpreter"
    SERPAPI_BASE_URL: str = "https://serpapi.com/search"
    SERPAPI_API_KEY: str = ""
    HTTP_USER_AGENT: str = "TripTailor/1.0 (https://github.com/AET-DevOps26/team-continuous-vacation)"
    PLACE_SEARCH_RADIUS_METERS: int = 8000
    PLACE_SEARCH_LIMIT: int = 40
    EVENT_SEARCH_LIMIT: int = 10
    OVERPASS_TIMEOUT_SECONDS: int = 12
    CACHE_TTL_SECONDS: int = 21600
    LOG_LEVEL: str = "INFO"


settings = Settings()
