from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


GENAI_SERVICE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=(GENAI_SERVICE_DIR / ".env.example", GENAI_SERVICE_DIR / ".env"),
        case_sensitive=True,
    )

    # GenAI Configuration
    LLM_PROVIDER: str
    AZURE_LLM_API_KEY: Optional[str] = None
    AZURE_LLM_BASE_URL: str
    AZURE_LLM_API_VERSION: str
    MODEL_NAME: str
    TEMPERATURE: float
    MAX_TOKENS: int

    # Local LLM Configuration
    LOCAL_LLM_API_KEY: str
    LOCAL_LLM_BASE_URL: str

    # Service Configuration
    LOG_LEVEL: str
    TRAVEL_CONTEXT_BASE_URL: str = "http://travel-context-service:8090"
    TRAVEL_CONTEXT_ENABLED: bool = True
    TRAVEL_CONTEXT_TIMEOUT_SECONDS: float = 20.0


settings = Settings()
