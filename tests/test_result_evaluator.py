"""Tests for ResultEvaluator — two-phase evaluation of extraction results."""

import json

from businessradar.llm_client import StubLLMClient
from businessradar.models import PageAnalysis
from businessradar.result_evaluator import ResultEvaluator


def _make_analysis(**overrides) -> PageAnalysis:
    defaults = dict(
        list_item_selector="div.vT-s-result",
        fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
        page_type="static",
    )
    defaults.update(overrides)
    return PageAnalysis(**defaults)


class TestStructureValidation:
    """Structure checks: empty data, missing/null core fields."""

    def test_empty_data_fails_structure(self) -> None:
        evaluator = ResultEvaluator(StubLLMClient(""))
        result = evaluator.evaluate([], "昨天的信息化采购公告", _make_analysis())

        assert result.structure_ok is False
        assert "数据为空" in result.issues

    def test_missing_core_field_fails_structure(self) -> None:
        data = [
            {"title": "测试公告", "link": "https://example.com/1"},
        ]
        evaluator = ResultEvaluator(StubLLMClient(""))
        result = evaluator.evaluate(data, "昨天的信息化采购公告", _make_analysis())

        assert result.structure_ok is False
        assert any("'date' 缺失" in issue for issue in result.issues)

    def test_null_core_field_fails_structure(self) -> None:
        data = [
            {"title": "测试公告", "date": None, "link": "https://example.com/1"},
        ]
        evaluator = ResultEvaluator(StubLLMClient(""))
        result = evaluator.evaluate(data, "昨天的信息化采购公告", _make_analysis())

        assert result.structure_ok is False
        assert any("'date' 值为空" in issue for issue in result.issues)


class TestSemanticValidation:
    """Semantic checks via stub LLM: data matches user query or not."""

    def _valid_data(self) -> list[dict]:
        return [
            {
                "title": "某市信息化采购公告",
                "date": "2026-06-01",
                "link": "https://example.com/1",
            }
        ]

    def test_semantic_ok_when_llm_confirms_match(self) -> None:
        stub = StubLLMClient(json.dumps({"matches": True, "reason": ""}))
        evaluator = ResultEvaluator(stub)
        result = evaluator.evaluate(
            self._valid_data(), "昨天的信息化采购公告", _make_analysis()
        )

        assert result.structure_ok is True
        assert result.semantic_ok is True
        assert result.issues == []

    def test_semantic_fail_when_llm_says_no_match(self) -> None:
        stub = StubLLMClient(json.dumps(
            {"matches": False, "reason": "返回的日期为 2026-06-01，但用户要求昨天的数据"}
        ))
        evaluator = ResultEvaluator(stub)
        result = evaluator.evaluate(
            self._valid_data(), "昨天的信息化采购公告", _make_analysis()
        )

        assert result.structure_ok is True
        assert result.semantic_ok is False
        assert any("日期" in issue for issue in result.issues)
