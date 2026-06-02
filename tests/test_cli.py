"""Tests for CLI behavior through its public interface."""

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
        import json
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
