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
