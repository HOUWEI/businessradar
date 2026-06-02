"""Tests for ScriptRunner — subprocess execution of generated scripts."""

from businessradar.script_runner import ScriptRunner


class TestScriptRunnerSuccess:
    """Script that prints valid JSON → RunResult(success=True, data=[...])."""

    def test_valid_json_output(self) -> None:
        script = (
            "import json\n"
            "data = [{'title': '测试公告', 'date': '2026-06-01', 'link': 'https://example.com/1'}]\n"
            "print(json.dumps(data, ensure_ascii=False))\n"
        )
        runner = ScriptRunner()
        result = runner.run(script)

        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["title"] == "测试公告"
        assert result.data[0]["date"] == "2026-06-01"
        assert result.error is None


class TestScriptRunnerFailure:
    """Script that crashes → RunResult(success=False, error=...)."""

    def test_crashing_script(self) -> None:
        script = "raise RuntimeError('page not found')\n"
        runner = ScriptRunner()
        result = runner.run(script)

        assert result.success is False
        assert result.data is None
        assert result.error is not None
        assert "RuntimeError" in result.error
        assert "page not found" in result.error


class TestScriptRunnerTimeout:
    """Script that hangs → timeout → RunResult(success=False, error=...)."""

    def test_hanging_script_times_out(self) -> None:
        script = "import time; time.sleep(300)\n"
        runner = ScriptRunner()
        result = runner.run(script, timeout=1)

        assert result.success is False
        assert result.data is None
        assert result.error is not None
        assert "timed out" in result.error
