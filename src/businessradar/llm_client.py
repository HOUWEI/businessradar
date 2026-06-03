"""LLMClient — protocol for LLM interaction, stub for testing, and real client."""

from typing import Protocol, runtime_checkable

from openai import OpenAI


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for calling an LLM with a text prompt."""

    def call(self, prompt: str) -> str:
        """Send prompt to LLM and return the text response."""
        ...


class StubLLMClient:
    """Test adapter: returns a fixed canned response for any prompt."""

    def __init__(self, response: str) -> None:
        self._response = response

    def call(self, prompt: str) -> str:
        return self._response


class RealLLMClient:
    """Production adapter: calls an OpenAI-compatible LLM API.

    Works with any OpenAI-compatible provider:
    - OpenAI: api_key="sk-...", model="gpt-4o"
    - 千问/DashScope: api_key="sk-...", model="qwen-plus",
      base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    - GLM/智谱: api_key="...", model="glm-4",
      base_url="https://open.bigmodel.cn/api/paas/v4"
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def call(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
