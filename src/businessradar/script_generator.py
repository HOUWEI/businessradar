"""ScriptGenerator — generates runnable Python scripts from PageAnalysis."""

from businessradar.llm_client import LLMClient
from businessradar.models import GeneratedScript, PageAnalysis


class ScriptGenerator:
    """Generate a Playwright + BeautifulSoup4 script from page analysis."""

    def __init__(self, llm_client: LLMClient, max_pages: int = 50) -> None:
        self._llm = llm_client
        self._max_pages = max_pages

    def generate(
        self,
        analysis: PageAnalysis,
        user_query: str,
        url: str,
        feedback: str | None = None,
    ) -> GeneratedScript:
        """Generate a Python scraping script based on the page analysis."""
        prompt = self._build_prompt(analysis, user_query, url, feedback)
        code = self._llm.call(prompt)
        return GeneratedScript(code=code)

    def _build_prompt(
        self,
        analysis: PageAnalysis,
        user_query: str,
        url: str,
        feedback: str | None = None,
    ) -> str:
        pagination_section = self._format_pagination(
            analysis.pagination, self._max_pages
        )
        filter_section = self._format_filter_params(analysis.filter_params)
        feedback_section = (
            f"\n上一次尝试的反馈：{feedback}\n请根据反馈调整脚本。\n"
            if feedback
            else ""
        )
        return (
            "根据以下页面分析结果，生成一个 Python 数据抓取脚本。\n\n"
            "要求：\n"
            "- 使用 playwright + BeautifulSoup4\n"
            "- 输出 JSON 数组到 stdout\n"
            "- 目标 URL: {url}\n"
            "- 用户查询: {query}\n"
            "- 列表项选择器: {selector}\n"
            "- 字段映射: {fields}\n"
            "- 页面类型: {page_type}\n"
            "{pagination}"
            "{filter}"
            "{feedback}"
            "只返回 Python 代码，不要其他内容。"
        ).format(
            url=url,
            query=user_query,
            selector=analysis.list_item_selector,
            fields=analysis.fields,
            page_type=analysis.page_type,
            pagination=pagination_section,
            filter=filter_section,
            feedback=feedback_section,
        )

    @staticmethod
    def _format_pagination(pagination, max_pages: int = 50) -> str:
        if pagination is None:
            return ""
        return (
            f"- 翻页机制: type={pagination.type}, "
            f"param_name={pagination.param_name}, "
            f"selector={pagination.selector}\n"
            "- 脚本必须包含翻页循环，自动抓取后续页面\n"
            "- 语义终止：根据用户查询推断何时停止翻页\n"
            f"- 硬上限：最多 {max_pages} 页\n"
        )

    @staticmethod
    def _format_filter_params(filter_params) -> str:
        if filter_params is None:
            return ""
        if filter_params.url_constructable:
            return (
                f"- 筛选方式: URL 参数筛选（url_constructable=True）\n"
                f"- 筛选参数: {filter_params.params}\n"
                "- 脚本应构造带筛选参数的 URL\n"
            )
        return (
            f"- 筛选方式: 本地过滤（url_constructable=False）\n"
            f"- 筛选参数: {filter_params.params}\n"
            "- 脚本应全量抓取后本地过滤数据\n"
        )
