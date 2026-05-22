from app.config.settings import settings
from app.services.llm.base import LLMProvider
from app.services.llm.openai_provider import AzureOpenAIProvider, OpenAIProvider


class LLMProviderFactory:
    """Factory to create LLM providers."""

    @staticmethod
    def get_provider() -> LLMProvider:
        """Create the configured provider implementation."""
        provider_type = settings.LLM_PROVIDER.lower()

        if provider_type == "azure":
            if not settings.AZURE_LLM_API_KEY:
                raise ValueError("AZURE_LLM_API_KEY is required when LLM_PROVIDER=azure")
            return AzureOpenAIProvider(
                api_key=settings.AZURE_LLM_API_KEY,
                base_url=settings.AZURE_LLM_BASE_URL,
                deployment_name=settings.MODEL_NAME,
                api_version=settings.AZURE_LLM_API_VERSION,
            )

        if provider_type == "local":
            return OpenAIProvider(
                api_key=settings.LOCAL_LLM_API_KEY,
                base_url=settings.LOCAL_LLM_BASE_URL,
                model_name=settings.MODEL_NAME,
            )

        raise ValueError(f"Unsupported LLM provider: {provider_type}")
