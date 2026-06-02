"""TrialLoop — orchestrates generate → run → evaluate → regenerate."""

from collections.abc import Callable

from businessradar.models import (
    Evaluation,
    FetchResult,
    RunResult,
)
from businessradar.page_analyzer import PageAnalyzer
from businessradar.result_evaluator import ResultEvaluator
from businessradar.script_generator import ScriptGenerator
from businessradar.script_runner import ScriptRunner

MAX_ROUNDS = 10
STAGNATION_THRESHOLD = 3

ProgressCallback = Callable[[int, str], None]
HumanInputCallback = Callable[[list[str]], str]


class TrialLoop:
    """Orchestrate the trial cycle with stagnation detection and human handoff."""

    def __init__(
        self,
        analyzer: PageAnalyzer,
        generator: ScriptGenerator,
        runner: ScriptRunner,
        evaluator: ResultEvaluator,
        progress_callback: ProgressCallback | None = None,
        human_input_callback: HumanInputCallback | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._generator = generator
        self._runner = runner
        self._evaluator = evaluator
        self._progress = progress_callback
        self._human_input = human_input_callback
        self._feedback: str | None = None

    def execute(
        self,
        url: str,
        query: str,
        fetch_result: FetchResult,
    ) -> RunResult:
        """Run the trial loop for up to MAX_ROUNDS with stagnation detection."""
        analysis = self._analyzer.analyze(fetch_result.html, query)
        last_issues_key: str | None = None
        stagnation_count = 0

        for round_num in range(1, MAX_ROUNDS + 1):
            script = self._generator.generate(
                analysis, query, url, feedback=self._feedback
            )
            run_result = self._runner.run(script.code)

            if not run_result.success:
                self._report_progress(round_num, f"脚本执行失败: {run_result.error}")
                issues_key = f"crash:{run_result.error}"
                stagnation_count, last_issues_key = self._track_stagnation(
                    issues_key, last_issues_key, stagnation_count
                )
                if stagnation_count >= STAGNATION_THRESHOLD:
                    result = self._handle_stagnation(round_num, [run_result.error or "未知错误"])
                    if result is not None:
                        return result
                    stagnation_count = 0
                    last_issues_key = None
                continue

            evaluation = self._evaluator.evaluate(
                run_result.data, query, analysis
            )

            if evaluation.structure_ok and evaluation.semantic_ok:
                self._report_progress(round_num, "成功")
                return run_result

            self._report_progress(
                round_num,
                f"评估未通过: {'; '.join(evaluation.issues)}",
            )

            issues_key = ";".join(sorted(evaluation.issues))
            stagnation_count, last_issues_key = self._track_stagnation(
                issues_key, last_issues_key, stagnation_count
            )

            if stagnation_count >= STAGNATION_THRESHOLD:
                result = self._handle_stagnation(round_num, evaluation.issues)
                if result is not None:
                    return result
                stagnation_count = 0
                last_issues_key = None

            if round_num >= MAX_ROUNDS:
                return RunResult(
                    success=False,
                    error=f"试错 {MAX_ROUNDS} 轮后仍未成功。问题：{'; '.join(evaluation.issues)}",
                )

        return RunResult(success=False, error="试错循环异常终止")

    def _handle_stagnation(
        self, round_num: int, issues: list[str]
    ) -> RunResult | None:
        """On stagnation, call human for input. Returns None if human gave feedback."""
        if self._human_input is None:
            return RunResult(
                success=False,
                error=f"连续 {STAGNATION_THRESHOLD} 轮出现相同问题，停滞终止。问题：{'; '.join(issues)}",
            )

        self._report_progress(round_num, "停滞检测，请求人工介入...")
        guidance = self._human_input(issues)
        if guidance:
            self._feedback = guidance
        return None

    @staticmethod
    def _track_stagnation(
        current_key: str,
        last_key: str | None,
        count: int,
    ) -> tuple[int, str]:
        """Track consecutive rounds with the same issues fingerprint."""
        if current_key == last_key:
            return count + 1, current_key
        return 1, current_key

    def _report_progress(self, round_num: int, message: str) -> None:
        """Call progress callback if configured."""
        if self._progress:
            self._progress(round_num, message)
