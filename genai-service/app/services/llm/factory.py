from app.config.settings import settings
from app.services.llm.base import LLMProvider
from app.services.llm.openai_provider import OpenAIProvider


class LLMProviderFactory:
    """Factory to create LLM providers."""

    @staticmethod
    def get_provider() -> LLMProvider:
        """Create the configured provider implementation."""
        provider_type = settings.LLM_PROVIDER.lower()

        if provider_type == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                model_name=settings.MODEL_NAME,
            )

        if provider_type == "local":
            return OpenAIProvider(
                api_key=settings.LOCAL_LLM_API_KEY,
                base_url=settings.LOCAL_LLM_BASE_URL,
                model_name=settings.MODEL_NAME,
            )

        raise ValueError(f"Unsupported LLM provider: {provider_type}")
