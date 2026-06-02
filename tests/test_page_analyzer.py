"""Tests for PageAnalyzer — LLM-driven HTML structure analysis."""

import json
from unittest.mock import MagicMock, patch

from businessradar.config import Config
from businessradar.models import PageAnalysis, PaginationInfo
from businessradar.page_analyzer import PageAnalyzer


def _make_config() -> Config:
    return Config(api_key="test-key", llm_model="gpt-4o")


SAMPLE_HTML = """
<html><body>
<div class="vT-s-result-list">
  <div class="vT-s-result">
    <a class="title" href="/detail/1">某市信息化采购公告</a>
    <span class="date">2026-06-01</span>
  </div>
</div>
</body></html>
"""

MOCK_LLM_RESPONSE = json.dumps({
    "list_item_selector": "div.vT-s-result",
    "fields": {
        "title": "a.title",
        "date": "span.date",
        "link": "a.title@href",
    },
    "page_type": "static",
})


class TestPageAnalyzerAnalysis:
    """Given HTML + query + mocked LLM → returns valid PageAnalysis."""

    @patch("businessradar.page_analyzer.PageAnalyzer._call_llm")
    def test_returns_page_analysis(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_RESPONSE

        analyzer = PageAnalyzer(_make_config())
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert isinstance(result, PageAnalysis)
        assert result.list_item_selector == "div.vT-s-result"
        assert "title" in result.fields
        assert "date" in result.fields
        assert "link" in result.fields
        assert result.page_type == "static"

    @patch("businessradar.page_analyzer.PageAnalyzer._call_llm")
    def test_passes_html_and_query_to_llm(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_RESPONSE

        analyzer = PageAnalyzer(_make_config())
        analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        mock_llm.assert_called_once()
        call_args = mock_llm.call_args[0][0]
        # The prompt should contain both the HTML and the user query
        assert "昨天的信息化采购公告" in call_args


class TestPaginationAnalysis:
    """PageAnalysis with pagination info from LLM."""

    @patch("businessradar.page_analyzer.PageAnalyzer._call_llm")
    def test_url_param_pagination(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = json.dumps({
            "list_item_selector": "div.vT-s-result",
            "fields": {"title": "a.title", "date": "span.date", "link": "a.title@href"},
            "page_type": "static",
            "pagination": {"type": "url_param", "param_name": "page"},
        })

        analyzer = PageAnalyzer(_make_config())
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert result.pagination is not None
        assert result.pagination.type == "url_param"
        assert result.pagination.param_name == "page"

    @patch("businessradar.page_analyzer.PageAnalyzer._call_llm")
    def test_backward_compat_no_pagination(self, mock_llm: MagicMock) -> None:
        # LLM returns no pagination field — existing behavior still works
        mock_llm.return_value = MOCK_LLM_RESPONSE

        analyzer = PageAnalyzer(_make_config())
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert result.pagination is None


class TestPageAnalyzerPromptIncludesPagination:
    """Prompt sent to LLM should ask about pagination."""

    @patch("businessradar.page_analyzer.PageAnalyzer._call_llm")
    def test_prompt_asks_about_pagination(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_RESPONSE

        analyzer = PageAnalyzer(_make_config())
        analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        prompt = mock_llm.call_args[0][0]
        assert "翻页" in prompt or "pagination" in prompt
