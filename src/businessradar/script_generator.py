"""ScriptGenerator — generates runnable Python scripts from PageAnalysis."""

from businessradar.config import Config
from businessradar.models import GeneratedScript, PageAnalysis


class ScriptGenerator:
    """Generate a Playwright + BeautifulSoup4 script from page analysis."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def generate(
        self, analysis: PageAnalysis, user_query: str, url: str
    ) -> GeneratedScript:
        """Generate a Python scraping script based on the page analysis.

        Sends the analysis, user query, and URL to an LLM to generate
        a complete, runnable Python script.
        """
        prompt = self._build_prompt(analysis, user_query, url)
        code = self._call_llm(prompt)
        return GeneratedScript(code=code)

    def _build_prompt(
        self, analysis: PageAnalysis, user_query: str, url: str
    ) -> str:
        return (
            "根据以下页面分析结果，生成一个 Python 数据抓取脚本。\n\n"
            "要求：\n"
            "- 使用 playwright + BeautifulSoup4\n"
            "- 输出 JSON 数组到 stdout\n"
            "- 目标 URL: {url}\n"
            "- 用户查询: {query}\n"
            "- 列表项选择器: {selector}\n"
            "- 字段映射: {fields}\n"
            "- 页面类型: {page_type}\n\n"
            "只返回 Python 代码，不要其他内容。"
        ).format(
            url=url,
            query=user_query,
            selector=analysis.list_item_selector,
            fields=analysis.fields,
            page_type=analysis.page_type,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the configured LLM. To be implemented with real provider."""
        raise NotImplementedError("LLM provider integration not yet implemented")
