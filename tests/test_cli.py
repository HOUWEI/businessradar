"""Tests for CLI behavior through its public interface."""

import json

from typer.testing import CliRunner

runner = CliRunner()


class TestCLIHelp:
    """CLI --help shows expected subcommands."""

    def test_help_shows_extract_command(self):
        from businessradar.cli import app

        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "extract" in result.output

    def test_extract_help_shows_required_args(self):
        from businessradar.cli import app

        result = runner.invoke(app, ["extract", "--help"])

        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--query" in result.output
        assert "--output" in result.output
        assert "--keywords" in result.output


class TestCLIDefaults:
    """CLI uses correct default values when no config provided."""

    def test_default_max_retries(self, tmp_path):
        from businessradar.config import load_config

        import yaml

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-test"}))

        config = load_config(config_path=str(config_file))

        assert config.max_retries == 10

    def test_default_max_pages(self, tmp_path):
        from businessradar.config import load_config

        import yaml

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-test"}))

        config = load_config(config_path=str(config_file))

        assert config.max_pages == 50

    def test_default_llm_provider(self, tmp_path):
        from businessradar.config import load_config

        import yaml

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-test"}))

        config = load_config(config_path=str(config_file))

        assert config.llm_provider == "openai"

    def test_default_proxy_is_none(self, tmp_path):
        from businessradar.config import load_config

        import yaml

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-test"}))

        config = load_config(config_path=str(config_file))

        assert config.proxy is None


class TestExtractEndToEnd:
    """CLI extract command wires PageFetcher + TrialLoop and outputs JSON."""

    def test_extract_outputs_json(self, tmp_path) -> None:
        from unittest.mock import patch

        from businessradar.cli import app
        from businessradar.config import Config
        from businessradar.models import FetchResult, RunResult

        mock_config = Config(api_key="sk-test")
        mock_data = [
            {"title": "测试公告", "date": "2026-06-01", "link": "https://example.com/1"}
        ]

        with (
            patch("businessradar.cli.PageFetcher") as MockFetcher,
            patch("businessradar.cli.TrialLoop") as MockLoop,
            patch("businessradar.cli.load_config") as mock_load,
        ):
            mock_load.return_value = mock_config
            MockFetcher.return_value.fetch.return_value = FetchResult(
                html="<html>list page</html>"
            )
            MockLoop.return_value.execute.return_value = RunResult(
                success=True, data=mock_data
            )

            result = runner.invoke(
                app,
                [
                    "--url",
                    "https://example.com/list",
                    "--query",
                    "昨天的信息化采购公告",
                ],
            )

        assert result.exit_code == 0
        output_data = json.loads(result.output.strip())
        assert len(output_data) == 1
        assert output_data[0]["title"] == "测试公告"

    def test_extract_writes_to_output_file(self, tmp_path) -> None:
        from unittest.mock import patch

        from businessradar.cli import app
        from businessradar.config import Config
        from businessradar.models import FetchResult, RunResult

        mock_config = Config(api_key="sk-test")
        mock_data = [
            {"title": "网络安全采购", "date": "2026-06-05", "link": "https://example.com/2"}
        ]
        output_file = tmp_path / "result.json"

        with (
            patch("businessradar.cli.PageFetcher") as MockFetcher,
            patch("businessradar.cli.TrialLoop") as MockLoop,
            patch("businessradar.cli.load_config") as mock_load,
        ):
            mock_load.return_value = mock_config
            MockFetcher.return_value.fetch.return_value = FetchResult(
                html="<html>list page</html>"
            )
            MockLoop.return_value.execute.return_value = RunResult(
                success=True, data=mock_data
            )

            result = runner.invoke(
                app,
                [
                    "--url", "https://example.com/list",
                    "--query", "昨天的信息化采购公告",
                    "--output", str(output_file),
                ],
            )

        assert result.exit_code == 0
        assert output_file.exists()
        saved = json.loads(output_file.read_text(encoding="utf-8"))
        assert len(saved) == 1
        assert saved[0]["title"] == "网络安全采购"


class TestKeywordsFile:
    """CLI --keywords merges keyword file into query."""

    def test_build_query_without_keywords(self):
        from businessradar.cli import _build_query

        result = _build_query("昨天的采购公告", None)
        assert result == "昨天的采购公告"

    def test_build_query_merges_keywords(self, tmp_path):
        from businessradar.cli import _build_query

        kw_file = tmp_path / "keywords.txt"
        kw_file.write_text("软件开发\n网络安全\n大数据\n", encoding="utf-8")

        result = _build_query("昨天的采购公告", str(kw_file))
        assert "昨天的采购公告" in result
        assert "软件开发" in result
        assert "网络安全" in result
        assert "大数据" in result

    def test_build_query_ignores_blank_lines(self, tmp_path):
        from businessradar.cli import _build_query

        kw_file = tmp_path / "keywords.txt"
        kw_file.write_text("软件开发\n\n\n大数据\n\n", encoding="utf-8")

        result = _build_query("采购", str(kw_file))
        assert "软件开发" in result
        assert "大数据" in result
        # Ensure no double separators from blank lines
        assert "、、" not in result

    def test_build_query_nonexistent_file_raises(self):
        import pytest

        from businessradar.cli import _build_query

        with pytest.raises(Exception):
            _build_query("采购", "/nonexistent/keywords.txt")

    def test_build_query_empty_file_returns_query_only(self, tmp_path):
        from businessradar.cli import _build_query

        kw_file = tmp_path / "keywords.txt"
        kw_file.write_text("\n\n\n", encoding="utf-8")

        result = _build_query("昨天的采购公告", str(kw_file))
        assert result == "昨天的采购公告"

    def test_extract_with_keywords_file(self, tmp_path) -> None:
        from unittest.mock import patch

        from businessradar.cli import app
        from businessradar.config import Config
        from businessradar.models import FetchResult, RunResult

        mock_config = Config(api_key="sk-test")
        mock_data = [{"title": "测试", "date": "2026-06-05", "link": "https://example.com/1"}]
        kw_file = tmp_path / "keywords.txt"
        kw_file.write_text("软件开发\n信息安全\n", encoding="utf-8")
        output_file = tmp_path / "result.json"

        with (
            patch("businessradar.cli.PageFetcher") as MockFetcher,
            patch("businessradar.cli.TrialLoop") as MockLoop,
            patch("businessradar.cli.load_config") as mock_load,
        ):
            mock_load.return_value = mock_config
            MockFetcher.return_value.fetch.return_value = FetchResult(html="<html></html>")
            MockLoop.return_value.execute.return_value = RunResult(
                success=True, data=mock_data
            )

            result = runner.invoke(
                app,
                [
                    "--url", "https://example.com/list",
                    "--query", "昨天的采购公告",
                    "--keywords", str(kw_file),
                    "--output", str(output_file),
                ],
            )

        assert result.exit_code == 0
        # Verify the merged query was passed to TrialLoop.execute
        call_args = MockLoop.return_value.execute.call_args
        merged_query = call_args[0][1]  # second positional arg is query
        assert "软件开发" in merged_query
        assert "信息安全" in merged_query
