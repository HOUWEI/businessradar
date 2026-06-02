"""Tests for ScriptGenerator — LLM-driven Python script generation."""

from unittest.mock import MagicMock, patch

from businessradar.config import Config
from businessradar.models import GeneratedScript, PageAnalysis
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
