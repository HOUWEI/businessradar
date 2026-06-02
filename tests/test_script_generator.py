"""Tests for ScriptGenerator — LLM-driven Python script generation."""

from businessradar.llm_client import StubLLMClient
from businessradar.models import FilterParams, GeneratedScript, PageAnalysis, PaginationInfo
from businessradar.script_generator import ScriptGenerator


SAMPLE_ANALYSIS = PageAnalysis(
    list_item_selector="div.vT-s-result",
    fields={
        "title": "a.title",
        "date": "span.date",
        "link": "a.title@href",
    },
    page_type="static",
)

MOCK_LLM_SCRIPT = (
    "from playwright.sync_api import sync_playwright\n"
    "from bs4 import BeautifulSoup\n"
    "import json\n\n"
    "with sync_playwright() as p:\n"
    "    browser = p.chromium.launch()\n"
    "    page = browser.new_page()\n"
    "    page.goto('https://example.com/list')\n"
    "    html = page.content()\n"
    "    browser.close()\n\n"
    "soup = BeautifulSoup(html, 'html.parser')\n"
    "items = soup.select('div.vT-s-result')\n"
    "results = []\n"
    "for item in items:\n"
    "    results.append({'title': item.select_one('a.title').text})\n"
    "print(json.dumps(results, ensure_ascii=False))\n"
)


class TestScriptGeneratorGeneration:
    """Given PageAnalysis + stub LLM → returns syntactically valid Python."""

    def test_returns_valid_python(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        gen = ScriptGenerator(stub)
        result = gen.generate(SAMPLE_ANALYSIS, "昨天的信息化采购公告", "https://example.com/list")

        assert isinstance(result, GeneratedScript)
        assert result.code.strip() != ""
        compile(result.code, "<generated>", "exec")

    def test_script_contains_playwright_and_bs4(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        gen = ScriptGenerator(stub)
        result = gen.generate(SAMPLE_ANALYSIS, "昨天的信息化采购公告", "https://example.com/list")

        assert "playwright" in result.code
        assert "BeautifulSoup" in result.code


class TestScriptGeneratorPagination:
    """ScriptGenerator passes pagination info to LLM prompt."""

    def test_prompt_includes_pagination_info(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            pagination=PaginationInfo(type="url_param", param_name="page"),
        )
        gen = ScriptGenerator(stub)
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = gen._build_prompt(analysis, "昨天的信息化采购公告", "https://example.com/list")
        assert "url_param" in prompt
        assert "page" in prompt

    def test_url_param_pagination_generates_valid_python(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            pagination=PaginationInfo(type="url_param", param_name="page"),
        )
        gen = ScriptGenerator(stub)
        result = gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        compile(result.code, "<generated>", "exec")
        assert "page" in result.code


class TestScriptGeneratorButtonPagination:
    """Button-click pagination in generated script."""

    def test_button_pagination_in_prompt(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="dynamic",
            pagination=PaginationInfo(type="button", selector="a.next-page"),
        )
        gen = ScriptGenerator(stub)
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = gen._build_prompt(analysis, "昨天的信息化采购公告", "https://example.com/list")
        assert "button" in prompt
        assert "a.next-page" in prompt


class TestScriptGeneratorFilterParams:
    """ScriptGenerator passes filter params to LLM prompt."""

    def test_url_filter_in_prompt(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            filter_params=FilterParams(
                url_constructable=True,
                params={"date_range": "2026-06-01", "category": "信息化"},
            ),
        )
        gen = ScriptGenerator(stub)
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = gen._build_prompt(analysis, "昨天的信息化采购公告", "https://example.com/list")
        assert "信息化" in prompt
        assert "url_constructable" in prompt or "URL" in prompt

    def test_local_filter_fallback_in_prompt(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            filter_params=FilterParams(
                url_constructable=False,
                params={"date_range": "2026-06-01"},
            ),
        )
        gen = ScriptGenerator(stub)
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = gen._build_prompt(analysis, "昨天的信息化采购公告", "https://example.com/list")
        assert "本地" in prompt or "local" in prompt or "过滤" in prompt


class TestScriptGeneratorMaxPagesFromConfig:
    """max_pages should come from constructor, not hardcoded."""

    def test_uses_custom_max_pages(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            pagination=PaginationInfo(type="url_param", param_name="page"),
        )
        gen = ScriptGenerator(stub, max_pages=20)
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = gen._build_prompt(analysis, "昨天的信息化采购公告", "https://example.com/list")
        assert "20 页" in prompt
        assert "50 页" not in prompt


class TestScriptGeneratorFeedback:
    """Feedback from human input is passed into the prompt."""

    def test_feedback_appears_in_prompt(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        gen = ScriptGenerator(stub)
        prompt = gen._build_prompt(
            SAMPLE_ANALYSIS,
            "昨天的信息化采购公告",
            "https://example.com/list",
            feedback="试试用 span.date 选择器",
        )
        assert "反馈" in prompt
        assert "span.date" in prompt

    def test_no_feedback_section_when_none(self) -> None:
        stub = StubLLMClient(MOCK_LLM_SCRIPT)
        gen = ScriptGenerator(stub)
        prompt = gen._build_prompt(
            SAMPLE_ANALYSIS,
            "昨天的信息化采购公告",
            "https://example.com/list",
        )
        assert "反馈" not in prompt
