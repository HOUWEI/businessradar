"""LLMClient — protocol for LLM interaction and stub for testing."""

from typing import Protocol, runtime_checkable


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
