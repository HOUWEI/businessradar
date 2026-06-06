"""Tests for TrialLoop — orchestrates generate → run → evaluate → regenerate."""

from dataclasses import dataclass, field
from typing import Optional

from businessradar.models import (
    Evaluation,
    FetchResult,
    GeneratedScript,
    PageAnalysis,
    RunResult,
)
from businessradar.page_analyzer import PageAnalyzer
from businessradar.result_evaluator import ResultEvaluator
from businessradar.script_generator import ScriptGenerator
from businessradar.script_runner import ScriptRunner
from businessradar.trial_loop import TrialLoop


def _make_analysis() -> PageAnalysis:
    return PageAnalysis(
        list_item_selector="div.vT-s-result",
        fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
        page_type="static",
    )


@dataclass
class MockAnalyzer:
    """Mock PageAnalyzer that returns a canned analysis."""
    analysis: PageAnalysis = field(default_factory=_make_analysis)
    call_count: int = 0

    def analyze(self, html: str, user_query: str) -> PageAnalysis:
        self.call_count += 1
        return self.analysis


@dataclass
class MockGenerator:
    """Mock ScriptGenerator that tracks calls."""
    script: GeneratedScript = field(default_factory=lambda: GeneratedScript(code="print('[]')"))
    call_count: int = 0
    last_feedback: str | None = None

    def generate(self, analysis, user_query, url, feedback=None):
        self.call_count += 1
        self.last_feedback = feedback
        return self.script


@dataclass
class MockRunner:
    """Mock ScriptRunner with configurable side effects."""
    results: list[RunResult] = field(default_factory=list)
    call_count: int = 0
    last_env: dict[str, str] | None = None

    def run(self, script_code, timeout=60, env=None):
        result = self.results[self.call_count] if self.call_count < len(self.results) else self.results[-1]
        self.call_count += 1
        self.last_env = env
        return result


@dataclass
class MockEvaluator:
    """Mock ResultEvaluator with configurable side effects."""
    results: list[Evaluation] = field(default_factory=list)
    call_count: int = 0

    def evaluate(self, data, user_query, page_analysis):
        result = self.results[self.call_count] if self.call_count < len(self.results) else self.results[-1]
        self.call_count += 1
        return result


FETCH_RESULT = FetchResult(html="<html>list page</html>")
MOCK_DATA = [{"title": "测试公告", "date": "2026-06-01", "link": "https://example.com/1"}]


class TestTrialLoopFirstRunPasses:
    """First generate→run→evaluate passes → returns data immediately."""

    def test_returns_data_on_first_success(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        runner = MockRunner(results=[RunResult(success=True, data=MOCK_DATA)])
        evaluator = MockEvaluator(results=[Evaluation(structure_ok=True, semantic_ok=True)])

        loop = TrialLoop(analyzer, generator, runner, evaluator)
        result = loop.execute("https://example.com", "测试查询", FETCH_RESULT)

        assert result.success is True
        assert result.data == MOCK_DATA
        assert generator.call_count == 1


class TestTrialLoopRetryOnFail:
    """First run fails evaluation, retry succeeds → returns retry data."""

    def test_retries_once_and_succeeds(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        retry_data = [{"title": "正确的公告", "date": "2026-06-01", "link": "https://example.com/2"}]
        runner = MockRunner(results=[
            RunResult(success=True, data=MOCK_DATA),
            RunResult(success=True, data=retry_data),
        ])
        evaluator = MockEvaluator(results=[
            Evaluation(structure_ok=True, semantic_ok=False, issues=["日期不匹配"]),
            Evaluation(structure_ok=True, semantic_ok=True),
        ])

        loop = TrialLoop(analyzer, generator, runner, evaluator)
        result = loop.execute("https://example.com", "昨天的公告", FETCH_RESULT)

        assert result.success is True
        assert result.data == retry_data
        assert generator.call_count == 2


class TestTrialLoopBothRoundsFail:
    """All 10 rounds fail with different issues → error report."""

    def test_returns_error_after_max_rounds(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        bad_data = [{"title": "测试", "link": "https://example.com/1"}]
        runner = MockRunner(results=[RunResult(success=True, data=bad_data)] * 10)
        evaluator = MockEvaluator(results=[
            Evaluation(structure_ok=False, semantic_ok=False, issues=[f"问题{i}"])
            for i in range(10)
        ])

        loop = TrialLoop(analyzer, generator, runner, evaluator)
        result = loop.execute("https://example.com", "昨天的公告", FETCH_RESULT)

        assert result.success is False
        assert result.error is not None
        assert "10" in result.error
        assert result.data is None


class TestTrialLoopExtendedRetry:
    """Full 10-round loop: can succeed on later rounds."""

    def test_succeeds_on_round_5(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        good_data = [{"title": "正确的公告", "date": "2026-06-01", "link": "https://example.com/2"}]
        runner = MockRunner(results=[
            RunResult(success=True, data=MOCK_DATA),
        ] * 4 + [RunResult(success=True, data=good_data)])
        evaluator = MockEvaluator(results=[
            Evaluation(structure_ok=True, semantic_ok=False, issues=[f"问题{i}"])
            for i in range(4)
        ] + [Evaluation(structure_ok=True, semantic_ok=True)])

        loop = TrialLoop(analyzer, generator, runner, evaluator)
        result = loop.execute("https://example.com", "昨天的公告", FETCH_RESULT)

        assert result.success is True
        assert result.data == good_data
        assert generator.call_count == 5


class TestTrialLoopStagnation:
    """3 consecutive rounds with identical issues → stops early."""

    def test_stops_on_stagnation(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        runner = MockRunner(results=[RunResult(success=True, data=MOCK_DATA)])
        evaluator = MockEvaluator(results=[
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"])
        ])

        loop = TrialLoop(analyzer, generator, runner, evaluator)
        result = loop.execute("https://example.com", "昨天的公告", FETCH_RESULT)

        assert result.success is False
        assert result.error is not None
        assert "停滞" in result.error
        assert generator.call_count == 3


class TestTrialLoopProgressCallback:
    """Progress callback is called each round with round number and status."""

    def test_calls_progress_each_round(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        runner = MockRunner(results=[
            RunResult(success=True, data=MOCK_DATA),
            RunResult(success=True, data=MOCK_DATA),
        ])
        evaluator = MockEvaluator(results=[
            Evaluation(structure_ok=True, semantic_ok=False, issues=["不匹配"]),
            Evaluation(structure_ok=True, semantic_ok=True),
        ])

        progress_calls: list[tuple[int, str]] = []

        def capture_progress(round_num: int, message: str) -> None:
            progress_calls.append((round_num, message))

        loop = TrialLoop(analyzer, generator, runner, evaluator, progress_callback=capture_progress)
        result = loop.execute("https://example.com", "昨天的公告", FETCH_RESULT)

        assert result.success is True
        assert len(progress_calls) == 2
        assert progress_calls[0][0] == 1
        assert progress_calls[1][0] == 2


class TestTrialLoopHumanInput:
    """When stagnation detected, invoke human_input_callback for user feedback."""

    def test_calls_human_input_and_feeds_back(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        good_data = [{"title": "正确的公告", "date": "2026-06-01", "link": "https://example.com/2"}]
        runner = MockRunner(results=[
            RunResult(success=True, data=MOCK_DATA),
            RunResult(success=True, data=MOCK_DATA),
            RunResult(success=True, data=MOCK_DATA),
            RunResult(success=True, data=good_data),
        ])
        evaluator = MockEvaluator(results=[
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"]),
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"]),
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"]),
            Evaluation(structure_ok=True, semantic_ok=True),
        ])

        human_calls: list[str] = []

        def human_callback(issues: list[str]) -> str:
            human_calls.append(";".join(issues))
            return "试试用 span.date 选择器"

        loop = TrialLoop(
            analyzer, generator, runner, evaluator,
            human_input_callback=human_callback,
        )
        result = loop.execute("https://example.com", "昨天的公告", FETCH_RESULT)

        assert result.success is True
        assert result.data == good_data
        assert len(human_calls) == 1
        assert "date" in human_calls[0]
        # Verify feedback was passed to the generator after human input
        assert generator.last_feedback == "试试用 span.date 选择器"


class TestTrialLoopLLMEnv:
    """TrialLoop passes llm_env to ScriptRunner."""

    def test_passes_llm_env_to_runner(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        runner = MockRunner(results=[RunResult(success=True, data=MOCK_DATA)])
        evaluator = MockEvaluator(results=[Evaluation(structure_ok=True, semantic_ok=True)])

        llm_env = {"BUSINESSRADAR_LLM_API_KEY": "sk-test", "BUSINESSRADAR_LLM_MODEL": "gpt-4o"}
        loop = TrialLoop(analyzer, generator, runner, evaluator, llm_env=llm_env)
        result = loop.execute("https://example.com", "测试查询", FETCH_RESULT)

        assert result.success is True
        assert runner.last_env == llm_env

    def test_no_llm_env_passes_none(self) -> None:
        analyzer = MockAnalyzer()
        generator = MockGenerator()
        runner = MockRunner(results=[RunResult(success=True, data=MOCK_DATA)])
        evaluator = MockEvaluator(results=[Evaluation(structure_ok=True, semantic_ok=True)])

        loop = TrialLoop(analyzer, generator, runner, evaluator)
        result = loop.execute("https://example.com", "测试查询", FETCH_RESULT)

        assert result.success is True
        assert runner.last_env is None
