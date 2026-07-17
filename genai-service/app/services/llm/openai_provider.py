import asyncio
import logging
from typing import Any

import httpx
from openai import APIError, APITimeoutError, AzureOpenAI

from app.observability.metrics import (
    LLM_REQUESTED_TOKENS,
    LLM_REQUESTED_TOKENS_TOTAL,
    LLM_USAGE_TOKENS_TOTAL,
)
from app.services.llm.base import LLMGenerationOptions, LLMProvider
from app.services.llm.base import (
    LLMProviderResponseError,
    LLMProviderTimeoutError,
)

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider using httpx for OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_name: str,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.http_client = client or httpx.AsyncClient(timeout=60.0)
        self._owns_client = client is None

    async def generate(self, prompt: str, options: LLMGenerationOptions) -> str:
        """
        Generate a response from the LLM using the OpenAI-compatible API.
        """
        self._record_requested_tokens("openai-compatible", options)
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(prompt, options)
        logger.debug(
            "Sending LLM request provider=openai-compatible base_url=%s model=%s "
            "json_mode=%s message_lengths=%s controls=%s",
            self.base_url,
            self.model_name,
            options.json_mode,
            _message_lengths(payload["messages"]),
            _generation_controls(payload),
        )

        try:
            response = await _post_with_retry(
                self.http_client,
                url,
                headers=headers,
                payload=payload,
            )
        except httpx.TimeoutException as error:
            raise LLMProviderTimeoutError("LLM request timed out") from error
        except httpx.HTTPError as error:
            raise LLMProviderResponseError("LLM request failed") from error

        try:
            logger.debug(
                "Received LLM HTTP response provider=openai-compatible "
                "status_code=%s response_bytes=%s",
                response.status_code,
                len(response.content),
            )

            if response.status_code != 200:
                raise LLMProviderResponseError(
                    f"OpenAI API error: {response.status_code}"
                )

            data = response.json()
            choice = data["choices"][0]
            content = choice["message"].get("content")
            _record_usage_tokens(
                provider="openai-compatible",
                model=self.model_name,
                usage=data.get("usage"),
            )
            logger.debug(
                "Parsed LLM response provider=openai-compatible finish_reason=%s "
                "usage=%s content_length=%s",
                choice.get("finish_reason"),
                data.get("usage"),
                len(content or ""),
            )
            if not content:
                raise LLMProviderResponseError(
                    "OpenAI-compatible response did not include message content "
                    f"(finish_reason={choice.get('finish_reason')}, usage={data.get('usage')})"
                )
            return str(content)
        except LLMProviderResponseError:
            raise
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise LLMProviderResponseError(
                "OpenAI-compatible response had an invalid structure"
            ) from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self.http_client.aclose()

    def _build_payload(
        self, prompt: str, options: LLMGenerationOptions
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": options.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        self._add_generation_controls(payload, options)
        if options.json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _add_generation_controls(
        self, payload: dict[str, Any], options: LLMGenerationOptions
    ) -> None:
        if _uses_completion_token_limit(self.model_name):
            payload["max_completion_tokens"] = options.max_tokens
            payload["reasoning_effort"] = "minimal"
            return

        payload["temperature"] = options.temperature
        payload["max_tokens"] = options.max_tokens

    def _record_requested_tokens(
        self, provider: str, options: LLMGenerationOptions
    ) -> None:
        labels = {"provider": provider, "model": self.model_name}
        LLM_REQUESTED_TOKENS.labels(**labels).observe(options.max_tokens)
        LLM_REQUESTED_TOKENS_TOTAL.labels(**labels).inc(options.max_tokens)


class AzureOpenAIProvider(OpenAIProvider):
    """Azure OpenAI provider using the official OpenAI Python SDK."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        deployment_name: str,
        api_version: str,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = deployment_name
        self._owns_client = False
        self.api_version = api_version
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=base_url,
            api_key=api_key,
        )

    async def generate(self, prompt: str, options: LLMGenerationOptions) -> str:
        """
        Generate a response from Azure OpenAI chat completions.
        """
        self._record_requested_tokens("azure", options)
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": options.system_prompt},
                {"role": "user", "content": prompt},
            ],
        }
        self._add_generation_controls(payload, options)
        if options.json_mode:
            payload["response_format"] = {"type": "json_object"}

        logger.debug(
            "Sending LLM request provider=azure base_url=%s deployment=%s "
            "api_version=%s json_mode=%s message_lengths=%s controls=%s",
            self.base_url,
            self.model_name,
            self.api_version,
            options.json_mode,
            _message_lengths(payload["messages"]),
            _generation_controls(payload),
        )
        try:
            response = await asyncio.to_thread(
                lambda: self.client.chat.completions.create(**payload)
            )
        except APITimeoutError as error:
            raise LLMProviderTimeoutError("Azure OpenAI request timed out") from error
        except APIError as error:
            raise LLMProviderResponseError("Azure OpenAI request failed") from error
        choice = response.choices[0]
        content = choice.message.content
        finish_reason = getattr(choice, "finish_reason", None)
        usage = _safe_model_dump(getattr(response, "usage", None))
        _record_usage_tokens(
            provider="azure",
            model=self.model_name,
            usage=usage,
        )
        logger.debug(
            "Received LLM response provider=azure finish_reason=%s usage=%s "
            "content_length=%s",
            finish_reason,
            usage,
            len(content or ""),
        )
        if not content:
            raise LLMProviderResponseError(
                "Azure OpenAI response did not include message content "
                f"(finish_reason={finish_reason}, usage={usage})"
            )
        return str(content)

    async def aclose(self) -> None:
        await asyncio.to_thread(self.client.close)


def _uses_completion_token_limit(model_name: str) -> bool:
    normalized_name = model_name.lower()
    return normalized_name.startswith("gpt-5") or normalized_name.startswith(
        ("o1", "o3", "o4", "o5")
    )


def _generation_controls(payload: dict[str, Any]) -> dict[str, Any]:
    control_keys = (
        "model",
        "temperature",
        "max_tokens",
        "max_completion_tokens",
        "reasoning_effort",
        "response_format",
    )
    return {key: payload[key] for key in control_keys if key in payload}


def _message_lengths(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "role": message.get("role"),
            "content_length": len(message.get("content") or ""),
        }
        for message in messages
    ]


def _safe_model_dump(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value


def _record_usage_tokens(provider: str, model: str, usage: Any) -> None:
    usage_dict = _safe_model_dump(usage)
    if not isinstance(usage_dict, dict):
        return

    token_fields = {
        "prompt": usage_dict.get("prompt_tokens"),
        "completion": usage_dict.get("completion_tokens"),
        "total": usage_dict.get("total_tokens"),
    }
    for token_type, value in token_fields.items():
        if isinstance(value, (int, float)):
            LLM_USAGE_TOKENS_TOTAL.labels(
                provider=provider,
                model=model,
                token_type=token_type,
            ).inc(value)


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    attempts: int = 3,
) -> httpx.Response:
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(attempts):
        try:
            response = await client.post(url, headers=headers, json=payload)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == attempts - 1:
                raise
        else:
            if response.status_code not in retryable_statuses or attempt == attempts - 1:
                return response
        await asyncio.sleep(0.1 * (2**attempt))
    raise RuntimeError("retry loop exited unexpectedly")
