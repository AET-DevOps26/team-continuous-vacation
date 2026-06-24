from types import SimpleNamespace

import pytest
import httpx

from app.services.llm.base import LLMGenerationOptions
from app.services.llm.factory import LLMProviderFactory
from app.services.llm.openai_provider import AzureOpenAIProvider, OpenAIProvider


class FakeChatCompletions:
    def __init__(self):
        self.payload = None

    def create(self, **payload):
        self.payload = payload
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"days": []}'),
                    finish_reason="stop",
                )
            ],
            usage=SimpleNamespace(total_tokens=42),
        )


class FakeAzureClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeChatCompletions())


@pytest.mark.asyncio
async def test_azure_provider_uses_deployment_and_completion_token_limit():
    provider = AzureOpenAIProvider(
        api_key="test-key",
        base_url="https://example.openai.azure.com/",
        deployment_name="gpt-5-nano",
        api_version="2024-12-01-preview",
    )
    fake_client = FakeAzureClient()
    provider.client = fake_client

    response = await provider.generate(
        prompt="Generate a trip",
        options=LLMGenerationOptions(
            temperature=0.7,
            max_tokens=16384,
            system_prompt="Return JSON",
            json_mode=True,
        ),
    )

    payload = fake_client.chat.completions.payload
    assert response == '{"days": []}'
    assert payload["model"] == "gpt-5-nano"
    assert payload["max_completion_tokens"] == 16384
    assert payload["reasoning_effort"] == "minimal"
    assert "max_tokens" not in payload
    assert "temperature" not in payload
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["messages"] == [
        {"role": "system", "content": "Return JSON"},
        {"role": "user", "content": "Generate a trip"},
    ]


@pytest.mark.asyncio
async def test_azure_provider_does_not_treat_ollama_as_reasoning_model():
    provider = AzureOpenAIProvider(
        api_key="test-key",
        base_url="https://example.openai.azure.com/",
        deployment_name="ollama",
        api_version="2024-12-01-preview",
    )
    fake_client = FakeAzureClient()
    provider.client = fake_client

    await provider.generate(
        prompt="Generate a trip",
        options=LLMGenerationOptions(
            temperature=0.7,
            max_tokens=2000,
            system_prompt="Return JSON",
            json_mode=False,
        ),
    )

    payload = fake_client.chat.completions.payload
    assert payload["max_tokens"] == 2000
    assert payload["temperature"] == 0.7
    assert "max_completion_tokens" not in payload
    assert "response_format" not in payload


@pytest.mark.asyncio
async def test_azure_provider_rejects_empty_content_with_metadata():
    provider = AzureOpenAIProvider(
        api_key="test-key",
        base_url="https://example.openai.azure.com/",
        deployment_name="gpt-5-nano",
        api_version="2024-12-01-preview",
    )
    fake_client = FakeAzureClient()
    fake_client.chat.completions.create = lambda **payload: SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=""),
                finish_reason="length",
            )
        ],
        usage=SimpleNamespace(total_tokens=2000),
    )
    provider.client = fake_client

    with pytest.raises(Exception) as exc_info:
        await provider.generate(
            prompt="Generate a trip",
            options=LLMGenerationOptions(
                temperature=0.7,
                max_tokens=2000,
                system_prompt="Return JSON",
                json_mode=True,
            ),
        )

    assert "did not include message content" in str(exc_info.value)
    assert "finish_reason=length" in str(exc_info.value)


def test_factory_creates_local_openai_compatible_provider(monkeypatch):
    monkeypatch.setattr("app.services.llm.factory.settings.LLM_PROVIDER", "local")
    monkeypatch.setattr("app.services.llm.factory.settings.LOCAL_LLM_API_KEY", "local-key")
    monkeypatch.setattr("app.services.llm.factory.settings.LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setattr("app.services.llm.factory.settings.MODEL_NAME", "llama3")

    provider = LLMProviderFactory.get_provider()

    assert isinstance(provider, OpenAIProvider)
    assert provider.api_key == "local-key"
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.model_name == "llama3"


def test_factory_rejects_unsupported_provider(monkeypatch):
    monkeypatch.setattr("app.services.llm.factory.settings.LLM_PROVIDER", "anthropic")

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMProviderFactory.get_provider()


@pytest.mark.asyncio
async def test_openai_compatible_provider_raises_on_http_error(monkeypatch):
    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None, timeout=None):
            return httpx.Response(
                500,
                text="model unavailable",
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr(httpx, "AsyncClient", FailingAsyncClient)
    provider = OpenAIProvider("test-key", "http://local-llm.example/v1", "llama3")

    with pytest.raises(Exception) as exc_info:
        await provider.generate(
            "Generate a trip",
            LLMGenerationOptions(
                temperature=0.7,
                max_tokens=1000,
                system_prompt="Return JSON",
                json_mode=True,
            ),
        )

    assert "OpenAI API error: 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_compatible_provider_propagates_timeout(monkeypatch):
    class TimingOutAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None, timeout=None):
            raise httpx.TimeoutException("request timed out")

    monkeypatch.setattr(httpx, "AsyncClient", TimingOutAsyncClient)
    provider = OpenAIProvider("test-key", "http://local-llm.example/v1", "llama3")

    with pytest.raises(httpx.TimeoutException, match="request timed out"):
        await provider.generate(
            "Generate a trip",
            LLMGenerationOptions(
                temperature=0.7,
                max_tokens=1000,
                system_prompt="Return JSON",
                json_mode=True,
            ),
        )
