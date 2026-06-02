"""Tests for ScriptGenerator — LLM-driven Python script generation."""

from unittest.mock import MagicMock, patch

from businessradar.config import Config
from businessradar.models import GeneratedScript, PageAnalysis, PaginationInfo, FilterParams
from businessradar.script_generator import ScriptGenerator


def _make_config() -> Config:
    return Config(api_key="test-key", llm_model="gpt-4o")


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
    """Given PageAnalysis + mocked LLM → returns syntactically valid Python."""

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_returns_valid_python(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_SCRIPT

        gen = ScriptGenerator(_make_config())
        result = gen.generate(SAMPLE_ANALYSIS, "昨天的信息化采购公告", "https://example.com/list")

        assert isinstance(result, GeneratedScript)
        assert result.code.strip() != ""
        # Verify it's syntactically valid Python
        compile(result.code, "<generated>", "exec")

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_script_contains_playwright_and_bs4(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_SCRIPT

        gen = ScriptGenerator(_make_config())
        result = gen.generate(SAMPLE_ANALYSIS, "昨天的信息化采购公告", "https://example.com/list")

        assert "playwright" in result.code
        assert "BeautifulSoup" in result.code


MOCK_PAGINATED_SCRIPT = (
    "from playwright.sync_api import sync_playwright\n"
    "from bs4 import BeautifulSoup\n"
    "import json\n\n"
    "results = []\n"
    "base_url = 'https://example.com/list'\n"
    "for page_num in range(1, 51):\n"
    "    url = f'{base_url}?page={page_num}'\n"
    "    with sync_playwright() as p:\n"
    "        browser = p.chromium.launch()\n"
    "        page = browser.new_page()\n"
    "        page.goto(url)\n"
    "        html = page.content()\n"
    "        browser.close()\n"
    "    soup = BeautifulSoup(html, 'html.parser')\n"
    "    items = soup.select('div.vT-s-result')\n"
    "    if not items:\n"
    "        break\n"
    "    for item in items:\n"
    "        results.append({'title': item.select_one('a.title').text})\n"
    "print(json.dumps(results, ensure_ascii=False))\n"
)


class TestScriptGeneratorPagination:
    """ScriptGenerator passes pagination info to LLM prompt."""

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_prompt_includes_pagination_info(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_PAGINATED_SCRIPT

        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            pagination=PaginationInfo(type="url_param", param_name="page"),
        )
        gen = ScriptGenerator(_make_config())
        result = gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        # The prompt sent to LLM should mention the pagination
        prompt = mock_llm.call_args[0][0]
        assert "url_param" in prompt
        assert "page" in prompt

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_url_param_pagination_generates_valid_python(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_PAGINATED_SCRIPT

        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            pagination=PaginationInfo(type="url_param", param_name="page"),
        )
        gen = ScriptGenerator(_make_config())
        result = gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        compile(result.code, "<generated>", "exec")
        assert "page" in result.code


class TestScriptGeneratorButtonPagination:
    """Button-click pagination in generated script."""

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_button_pagination_in_prompt(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_SCRIPT

        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="dynamic",
            pagination=PaginationInfo(type="button", selector="a.next-page"),
        )
        gen = ScriptGenerator(_make_config())
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = mock_llm.call_args[0][0]
        assert "button" in prompt
        assert "a.next-page" in prompt


class TestScriptGeneratorFilterParams:
    """ScriptGenerator passes filter params to LLM prompt."""

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_url_filter_in_prompt(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_SCRIPT

        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            filter_params=FilterParams(
                url_constructable=True,
                params={"date_range": "2026-06-01", "category": "信息化"},
            ),
        )
        gen = ScriptGenerator(_make_config())
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = mock_llm.call_args[0][0]
        assert "信息化" in prompt
        assert "url_constructable" in prompt or "URL" in prompt

    @patch("businessradar.script_generator.ScriptGenerator._call_llm")
    def test_local_filter_fallback_in_prompt(self, mock_llm: MagicMock) -> None:
        mock_llm.return_value = MOCK_LLM_SCRIPT

        analysis = PageAnalysis(
            list_item_selector="div.vT-s-result",
            fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
            page_type="static",
            filter_params=FilterParams(
                url_constructable=False,
                params={"date_range": "2026-06-01"},
            ),
        )
        gen = ScriptGenerator(_make_config())
        gen.generate(analysis, "昨天的信息化采购公告", "https://example.com/list")

        prompt = mock_llm.call_args[0][0]
        # Should mention local filtering as fallback
        assert "本地" in prompt or "local" in prompt or "过滤" in prompt
