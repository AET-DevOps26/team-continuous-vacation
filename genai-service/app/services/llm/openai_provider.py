import httpx
from app.services.llm.base import LLMGenerationOptions, LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI provider using httpx for OpenAI-compatible APIs."""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    async def generate(self, prompt: str, options: LLMGenerationOptions) -> str:
        """
        Generate a response from the LLM using the OpenAI-compatible API.
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": options.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": options.temperature,
            "max_tokens": options.max_tokens,
        }
        if options.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, headers=headers, json=payload, timeout=60.0
            )

            if response.status_code != 200:
                raise Exception(
                    f"OpenAI API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            return data["choices"][0]["message"]["content"]
