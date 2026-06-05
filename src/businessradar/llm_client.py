"""LLMClient — protocol for LLM interaction, stub for testing, and real client."""

import base64
from typing import Protocol, runtime_checkable

from openai import OpenAI


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for calling an LLM with a text prompt."""

    def call(self, prompt: str) -> str:
        """Send prompt to LLM and return the text response."""
        ...

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        """Send prompt + image to LLM and return the text response."""
        ...


class StubLLMClient:
    """Test adapter: returns a fixed canned response for any prompt."""

    def __init__(self, response: str, vision_response: str | None = None) -> None:
        self._response = response
        self._vision_response = vision_response or response

    def call(self, prompt: str) -> str:
        return self._response

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        return self._vision_response


class RealLLMClient:
    """Production adapter: calls an OpenAI-compatible LLM API.

    Works with any OpenAI-compatible provider:
    - OpenAI: api_key="sk-...", model="gpt-4o"
    - 千问/DashScope: api_key="sk-...", model="qwen-plus",
      base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    - GLM/智谱: api_key="...", model="glm-4v-flash",
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

    def call_vision(self, prompt: str, image_bytes: bytes) -> str:
        """Send text prompt + image to LLM vision endpoint."""
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content
