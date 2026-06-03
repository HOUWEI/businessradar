"""Tests for RealLLMClient — actual LLM SDK integration."""

from unittest.mock import MagicMock, patch

from businessradar.config import Config
from businessradar.llm_client import RealLLMClient


class TestRealLLMClient:
    """RealLLMClient uses openai SDK with configurable base_url."""

    @patch("businessradar.llm_client.OpenAI")
    def test_calls_openai_sdk(self, mock_openai_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="分析结果"))]
        mock_client.chat.completions.create.return_value = mock_response

        client = RealLLMClient(
            api_key="sk-test",
            model="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        result = client.call("分析这个页面")

        assert result == "分析结果"
        mock_openai_cls.assert_called_once_with(
            api_key="sk-test",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        mock_client.chat.completions.create.assert_called_once_with(
            model="qwen-plus",
            messages=[{"role": "user", "content": "分析这个页面"}],
        )

    @patch("businessradar.llm_client.OpenAI")
    def test_works_without_base_url(self, mock_openai_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_client.chat.completions.create.return_value = mock_response

        client = RealLLMClient(api_key="sk-test", model="gpt-4o")
        result = client.call("test")

        assert result == "ok"
        mock_openai_cls.assert_called_once_with(api_key="sk-test", base_url=None)

    @patch("businessradar.llm_client.OpenAI")
    def test_satisfies_llm_client_protocol(self, mock_openai_cls: MagicMock) -> None:
        from businessradar.llm_client import LLMClient

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="result"))]
        mock_client.chat.completions.create.return_value = mock_response

        client: LLMClient = RealLLMClient(api_key="sk-test", model="qwen-turbo")
        assert client.call("prompt") == "result"
