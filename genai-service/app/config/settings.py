from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # GenAI Configuration
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-4"
    TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 2000

    # Local LLM Configuration
    LOCAL_LLM_API_KEY: str = "ollama"
    LOCAL_LLM_BASE_URL: str = "http://localhost:11434/v1"

    # Service Configuration
    LOG_LEVEL: str = "INFO"


settings = Settings()
