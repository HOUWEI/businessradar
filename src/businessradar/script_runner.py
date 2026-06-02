"""ScriptRunner — executes generated scripts in subprocess, captures JSON output."""

import json
import subprocess
import tempfile
from pathlib import Path

from businessradar.models import RunResult


class ScriptRunner:
    """Run a generated Python script and capture its JSON output."""

    def run(self, script_code: str, timeout: int = 60) -> RunResult:
        """Execute script_code in a subprocess and return parsed result.

        The script is expected to print a JSON array to stdout.
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp:
            tmp.write(script_code)
            tmp_path = Path(tmp.name)

        try:
            proc = subprocess.run(
                ["python3", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return RunResult(success=False, error=f"Script timed out after {timeout}s")
        finally:
            tmp_path.unlink(missing_ok=True)

        if proc.returncode != 0:
            return RunResult(
                success=False,
                error=proc.stderr.strip() or f"Exit code {proc.returncode}",
            )

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            return RunResult(success=False, error=f"Invalid JSON output: {e}")

        return RunResult(success=True, data=data)
