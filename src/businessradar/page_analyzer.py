"""PageAnalyzer — calls LLM to analyze HTML structure and identify selectors."""

import json

from businessradar.config import Config
from businessradar.models import PageAnalysis


class PageAnalyzer:
    """Analyze page HTML via LLM to extract structure information."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def analyze(self, html: str, user_query: str) -> PageAnalysis:
        """Analyze HTML structure and return a PageAnalysis.

        Sends the HTML and user query to an LLM, asking it to identify
        list item selectors, field mappings, and page type.
        """
        prompt = self._build_prompt(html, user_query)
        response = self._call_llm(prompt)
        return self._parse_response(response)

    def _build_prompt(self, html: str, user_query: str) -> str:
        return (
            "分析以下 HTML 页面结构。用户查询：{query}\n\n"
            "请返回 JSON 格式：\n"
            "- list_item_selector: 列表项的 CSS 选择器\n"
            "- fields: 字段名到 CSS 选择器的映射（必须包含 title, date, link）\n"
            "- page_type: 'static' 或 'dynamic'\n\n"
            "HTML:\n{html}"
        ).format(query=user_query, html=html)

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM. To be implemented with real provider."""
        raise NotImplementedError("LLM provider integration not yet implemented")

    def _parse_response(self, response: str) -> PageAnalysis:
        """Parse LLM JSON response into PageAnalysis."""
        data = json.loads(response)
        return PageAnalysis(**data)
