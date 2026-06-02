"""Tests for TrialLoop — orchestrates generate → run → evaluate → regenerate."""

from unittest.mock import MagicMock, patch

from businessradar.config import Config
from businessradar.models import (
    Evaluation,
    FetchResult,
    GeneratedScript,
    PageAnalysis,
    RunResult,
)
from businessradar.trial_loop import TrialLoop


def _make_config() -> Config:
    return Config(api_key="test-key")


def _make_analysis() -> PageAnalysis:
    return PageAnalysis(
        list_item_selector="div.vT-s-result",
        fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
        page_type="static",
    )


class TestTrialLoopFirstRunPasses:
    """First generate→run→evaluate passes → returns data immediately."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_returns_data_on_first_success(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        mock_data = [
            {"title": "测试公告", "date": "2026-06-01", "link": "https://example.com/1"}
        ]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script
        MockRunner.return_value.run.return_value = RunResult(
            success=True, data=mock_data
        )
        MockEvaluator.return_value.evaluate.return_value = Evaluation(
            structure_ok=True, semantic_ok=True
        )

        loop = TrialLoop(_make_config())
        result = loop.execute("https://example.com", "测试查询", fetch_result)

        assert result.success is True
        assert result.data == mock_data
        # Should NOT have retried — generator called exactly once
        MockGenerator.return_value.generate.assert_called_once()


class TestTrialLoopRetryOnFail:
    """First run fails evaluation, retry succeeds → returns retry data."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_retries_once_and_succeeds(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        first_data = [{"title": "测试", "date": "2026-06-01", "link": "https://example.com/1"}]
        retry_data = [{"title": "正确的公告", "date": "2026-06-01", "link": "https://example.com/2"}]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script

        # First run: success but evaluation fails; second run: success + evaluation passes
        MockRunner.return_value.run.side_effect = [
            RunResult(success=True, data=first_data),
            RunResult(success=True, data=retry_data),
        ]
        MockEvaluator.return_value.evaluate.side_effect = [
            Evaluation(structure_ok=True, semantic_ok=False, issues=["日期不匹配"]),
            Evaluation(structure_ok=True, semantic_ok=True),
        ]

        loop = TrialLoop(_make_config())
        result = loop.execute("https://example.com", "昨天的公告", fetch_result)

        assert result.success is True
        assert result.data == retry_data
        # Generator called twice — once per round
        assert MockGenerator.return_value.generate.call_count == 2


class TestTrialLoopBothRoundsFail:
    """All 10 rounds fail with different issues → error report."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_returns_error_after_max_rounds(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        bad_data = [{"title": "测试", "link": "https://example.com/1"}]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script
        # 10 rounds of failure, each with a different issue (avoids stagnation)
        MockRunner.return_value.run.side_effect = [
            RunResult(success=True, data=bad_data)
        ] * 10
        MockEvaluator.return_value.evaluate.side_effect = [
            Evaluation(
                structure_ok=False,
                semantic_ok=False,
                issues=[f"问题{i}"],
            )
            for i in range(10)
        ]

        loop = TrialLoop(_make_config())
        result = loop.execute("https://example.com", "昨天的公告", fetch_result)

        assert result.success is False
        assert result.error is not None
        assert "10" in result.error
        assert result.data is None


class TestTrialLoopExtendedRetry:
    """Full 10-round loop: can succeed on later rounds."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_succeeds_on_round_5(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        bad_data = [{"title": "测试", "date": "2026-06-01", "link": "https://example.com/1"}]
        good_data = [{"title": "正确的公告", "date": "2026-06-01", "link": "https://example.com/2"}]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script
        MockRunner.return_value.run.side_effect = [
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=good_data),
        ]
        MockEvaluator.return_value.evaluate.side_effect = [
            Evaluation(structure_ok=True, semantic_ok=False, issues=[f"问题{i}"])
            for i in range(4)
        ] + [
            Evaluation(structure_ok=True, semantic_ok=True),
        ]

        loop = TrialLoop(_make_config())
        result = loop.execute("https://example.com", "昨天的公告", fetch_result)

        assert result.success is True
        assert result.data == good_data
        assert MockGenerator.return_value.generate.call_count == 5


class TestTrialLoopStagnation:
    """3 consecutive rounds with identical issues → stops early."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_stops_on_stagnation(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        bad_data = [{"title": "测试", "link": "https://example.com/1"}]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script
        MockRunner.return_value.run.return_value = RunResult(
            success=True, data=bad_data
        )
        # Same issue repeated 10 times — should stagnate after 3
        stagnant_issue = Evaluation(
            structure_ok=False,
            semantic_ok=False,
            issues=["核心字段 'date' 缺失"],
        )
        MockEvaluator.return_value.evaluate.return_value = stagnant_issue

        loop = TrialLoop(_make_config())
        result = loop.execute("https://example.com", "昨天的公告", fetch_result)

        assert result.success is False
        assert result.error is not None
        assert "停滞" in result.error
        # Should have stopped at round 3, not gone all 10
        assert MockGenerator.return_value.generate.call_count == 3


class TestTrialLoopProgressCallback:
    """Progress callback is called each round with round number and status."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_calls_progress_each_round(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        mock_data = [
            {"title": "测试公告", "date": "2026-06-01", "link": "https://example.com/1"}
        ]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script
        MockRunner.return_value.run.side_effect = [
            RunResult(success=True, data=mock_data),  # round 1: fail eval
            RunResult(success=True, data=mock_data),  # round 2: pass
        ]
        MockEvaluator.return_value.evaluate.side_effect = [
            Evaluation(structure_ok=True, semantic_ok=False, issues=["不匹配"]),
            Evaluation(structure_ok=True, semantic_ok=True),
        ]

        progress_calls: list[tuple[int, str]] = []

        def capture_progress(round_num: int, message: str) -> None:
            progress_calls.append((round_num, message))

        loop = TrialLoop(_make_config(), progress_callback=capture_progress)
        result = loop.execute("https://example.com", "昨天的公告", fetch_result)

        assert result.success is True
        assert len(progress_calls) == 2
        # Each call is (round_num, message)
        assert progress_calls[0][0] == 1
        assert progress_calls[1][0] == 2


class TestTrialLoopHumanInput:
    """When stagnation detected, invoke human_input_callback for user feedback."""

    @patch("businessradar.trial_loop.ResultEvaluator")
    @patch("businessradar.trial_loop.ScriptRunner")
    @patch("businessradar.trial_loop.ScriptGenerator")
    @patch("businessradar.trial_loop.PageAnalyzer")
    def test_calls_human_input_on_stagnation(
        self,
        MockAnalyzer: MagicMock,
        MockGenerator: MagicMock,
        MockRunner: MagicMock,
        MockEvaluator: MagicMock,
    ) -> None:
        fetch_result = FetchResult(html="<html>list page</html>")
        analysis = _make_analysis()
        script = GeneratedScript(code="print('[]')")
        good_data = [
            {"title": "正确的公告", "date": "2026-06-01", "link": "https://example.com/2"}
        ]
        bad_data = [
            {"title": "测试", "link": "https://example.com/1"}
        ]

        MockAnalyzer.return_value.analyze.return_value = analysis
        MockGenerator.return_value.generate.return_value = script

        # 3 stagnant rounds, then human gives advice, then round 4 succeeds
        MockRunner.return_value.run.side_effect = [
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=bad_data),
            RunResult(success=True, data=good_data),
        ]
        MockEvaluator.return_value.evaluate.side_effect = [
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"]),
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"]),
            Evaluation(structure_ok=False, semantic_ok=False, issues=["核心字段 'date' 缺失"]),
            Evaluation(structure_ok=True, semantic_ok=True),
        ]

        human_calls: list[str] = []

        def human_callback(issues: list[str]) -> str:
            human_calls.append(";".join(issues))
            return "试试用 span.date 选择器"

        loop = TrialLoop(_make_config(), human_input_callback=human_callback)
        result = loop.execute("https://example.com", "昨天的公告", fetch_result)

        assert result.success is True
        assert result.data == good_data
        # Human was called once (on stagnation after round 3)
        assert len(human_calls) == 1
        assert "date" in human_calls[0]
