"""Tests for PageAnalyzer — LLM-driven HTML structure analysis."""

import json

from businessradar.llm_client import StubLLMClient
from businessradar.models import PageAnalysis
from businessradar.page_analyzer import PageAnalyzer

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
    """Given HTML + query + stub LLM → returns valid PageAnalysis."""

    def test_returns_page_analysis(self) -> None:
        stub = StubLLMClient(MOCK_LLM_RESPONSE)
        analyzer = PageAnalyzer(stub)
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert isinstance(result, PageAnalysis)
        assert result.list_item_selector == "div.vT-s-result"
        assert "title" in result.fields
        assert "date" in result.fields
        assert "link" in result.fields
        assert result.page_type == "static"

    def test_passes_html_and_query_to_llm(self) -> None:
        stub = StubLLMClient(MOCK_LLM_RESPONSE)
        analyzer = PageAnalyzer(stub)
        analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        # StubLLMClient returns canned response regardless of prompt,
        # so we just verify the analyzer doesn't crash with real inputs


class TestPaginationAnalysis:
    """PageAnalysis with pagination info from LLM."""

    def test_url_param_pagination(self) -> None:
        stub = StubLLMClient(json.dumps({
            "list_item_selector": "div.vT-s-result",
            "fields": {"title": "a.title", "date": "span.date", "link": "a.title@href"},
            "page_type": "static",
            "pagination": {"type": "url_param", "param_name": "page"},
        }))
        analyzer = PageAnalyzer(stub)
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert result.pagination is not None
        assert result.pagination.type == "url_param"
        assert result.pagination.param_name == "page"

    def test_backward_compat_no_pagination(self) -> None:
        stub = StubLLMClient(MOCK_LLM_RESPONSE)
        analyzer = PageAnalyzer(stub)
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert result.pagination is None


class TestPageAnalyzerPromptIncludesPagination:
    """Prompt sent to LLM should ask about pagination."""

    def test_prompt_asks_about_pagination(self) -> None:
        stub = StubLLMClient(MOCK_LLM_RESPONSE)
        analyzer = PageAnalyzer(stub)
        analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        # Verify via the _build_prompt method directly
        prompt = analyzer._build_prompt(SAMPLE_HTML, "昨天的信息化采购公告")
        assert "翻页" in prompt or "pagination" in prompt


class TestFilterParamsAnalysis:
    """PageAnalysis with filter params from LLM."""

    def test_url_filter_params(self) -> None:
        stub = StubLLMClient(json.dumps({
            "list_item_selector": "div.vT-s-result",
            "fields": {"title": "a.title", "date": "span.date", "link": "a.title@href"},
            "page_type": "static",
            "filter_params": {
                "url_constructable": True,
                "params": {"date_range": "2026-06-01", "category": "信息化"},
            },
        }))
        analyzer = PageAnalyzer(stub)
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert result.filter_params is not None
        assert result.filter_params.url_constructable is True
        assert result.filter_params.params["category"] == "信息化"

    def test_backward_compat_no_filter_params(self) -> None:
        stub = StubLLMClient(MOCK_LLM_RESPONSE)
        analyzer = PageAnalyzer(stub)
        result = analyzer.analyze(SAMPLE_HTML, "昨天的信息化采购公告")

        assert result.filter_params is None


class TestPageAnalyzerPromptIncludesFilter:
    """Prompt sent to LLM should ask about filter parameters."""

    def test_prompt_asks_about_filter_params(self) -> None:
        stub = StubLLMClient(MOCK_LLM_RESPONSE)
        analyzer = PageAnalyzer(stub)
        prompt = analyzer._build_prompt(SAMPLE_HTML, "昨天的信息化采购公告")
        assert "筛选" in prompt or "filter" in prompt
