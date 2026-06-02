"""Tests for LLMClient protocol and StubLLMClient."""

from businessradar.llm_client import LLMClient, StubLLMClient


class TestStubLLMClient:
    """StubLLMClient returns canned responses."""

    def test_returns_canned_response(self) -> None:
        stub = StubLLMClient('{"result": "ok"}')
        assert stub.call("any prompt") == '{"result": "ok"}'

    def test_satisfies_protocol(self) -> None:
        stub = StubLLMClient("response")
        # Should be usable as an LLMClient
        client: LLMClient = stub
        assert client.call("prompt") == "response"
