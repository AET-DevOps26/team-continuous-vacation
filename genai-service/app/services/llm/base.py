from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMGenerationOptions:
    """Provider-neutral generation controls."""

    temperature: float
    max_tokens: int
    system_prompt: str
    json_mode: bool = True


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str, options: LLMGenerationOptions) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The prompt to send to the LLM.
            options: Provider-neutral generation settings.

        Returns:
            The LLM response as a string.
        """
        pass

    async def aclose(self) -> None:
        """Release provider resources when the application shuts down."""


class LLMProviderError(RuntimeError):
    """Base error for expected LLM provider failures."""


class LLMProviderResponseError(LLMProviderError):
    """The provider returned an unsuccessful or malformed response."""


class LLMProviderTimeoutError(LLMProviderError):
    """The provider did not respond before the configured timeout."""
