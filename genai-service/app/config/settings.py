from pathlib import Path
from typing import Optional

from pydantic import model_validator
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
    AZURE_LLM_API_KEY_FILE: Optional[Path] = None
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

    @model_validator(mode="after")
    def load_secrets_from_files(self):
        """Load Docker secret file values when direct env values are not set."""
        if not self.AZURE_LLM_API_KEY and self.AZURE_LLM_API_KEY_FILE:
            self.AZURE_LLM_API_KEY = self.AZURE_LLM_API_KEY_FILE.read_text().strip()
        return self


settings = Settings()
