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
    OPEN_METEO_FORECAST_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPEN_METEO_ARCHIVE_BASE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    WEATHER_ENABLED: bool = True
    # Open-Meteo's free forecast covers an inclusive 16-day window (today .. today+15),
    # so the furthest forecastable date is 15 days out. Anything beyond falls back to
    # the same calendar dates from the previous year via the historical archive API.
    WEATHER_FORECAST_MAX_DAYS: int = 15
    HTTP_USER_AGENT: str = "TripTailor/1.0 (https://github.com/AET-DevOps26/team-continuous-vacation)"
    PLACE_SEARCH_RADIUS_METERS: int = 8000
    PLACE_SEARCH_LIMIT: int = 40
    EVENT_SEARCH_LIMIT: int = 10
    OVERPASS_TIMEOUT_SECONDS: int = 12
    CACHE_TTL_SECONDS: int = 21600
    LOG_LEVEL: str = "INFO"


settings = Settings()
