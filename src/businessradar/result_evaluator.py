"""ResultEvaluator — two-phase evaluation of extraction results."""

import json

from businessradar.llm_client import LLMClient
from businessradar.models import Evaluation, PageAnalysis

CORE_FIELDS = ("title", "date", "link")


class ResultEvaluator:
    """Evaluate extraction results in two phases: structure then semantic."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def evaluate(
        self,
        data: list[dict],
        user_query: str,
        page_analysis: PageAnalysis,
    ) -> Evaluation:
        """Run structure validation, then semantic validation via LLM."""
        structure_ok, issues, suggestions = self._check_structure(data, page_analysis)

        if not structure_ok:
            return Evaluation(
                structure_ok=False,
                semantic_ok=False,
                issues=issues,
                suggestions=suggestions,
            )

        semantic_ok, sem_issues, sem_suggestions = self._check_semantic(
            data, user_query
        )
        return Evaluation(
            structure_ok=True,
            semantic_ok=semantic_ok,
            issues=sem_issues,
            suggestions=sem_suggestions,
        )

    def _check_structure(
        self, data: list[dict], page_analysis: PageAnalysis
    ) -> tuple[bool, list[str], list[str]]:
        """Phase 1: structural validation — non-empty, core fields present and non-null."""
        issues: list[str] = []
        suggestions: list[str] = []

        if not data:
            issues.append("数据为空")
            return False, issues, suggestions

        for field in CORE_FIELDS:
            missing_rows = [i for i, row in enumerate(data) if field not in row]
            if len(missing_rows) == len(data):
                issues.append(f"核心字段 '{field}' 缺失")
                selector = page_analysis.fields.get(field, "")
                suggestions.append(f"检查选择器 '{selector}' 是否正确")

        for field in CORE_FIELDS:
            null_rows = [
                i
                for i, row in enumerate(data)
                if field in row and not row[field]
            ]
            if len(null_rows) == len(data):
                issues.append(f"核心字段 '{field}' 值为空")
                selector = page_analysis.fields.get(field, "")
                suggestions.append(f"检查选择器 '{selector}' 提取的值是否为空")

        ok = len(issues) == 0
        return ok, issues, suggestions

    def _check_semantic(
        self, data: list[dict], user_query: str
    ) -> tuple[bool, list[str], list[str]]:
        """Phase 2: semantic validation via LLM."""
        prompt = self._build_semantic_prompt(data, user_query)
        response = self._llm.call(prompt)
        return self._parse_semantic_response(response)

    def _build_semantic_prompt(self, data: list[dict], user_query: str) -> str:
        return (
            "判断以下抓取数据是否匹配用户的查询需求。\n\n"
            "用户查询：{query}\n\n"
            "抓取数据：\n{data}\n\n"
            "请返回 JSON：{{\"matches\": true/false, \"reason\": \"不匹配的原因\"}}"
        ).format(query=user_query, data=json.dumps(data[:5], ensure_ascii=False))

    def _parse_semantic_response(
        self, response: str
    ) -> tuple[bool, list[str], list[str]]:
        result = json.loads(response)
        matches = result.get("matches", False)
        reason = result.get("reason", "")
        issues = [reason] if not matches and reason else []
        return matches, issues, []
