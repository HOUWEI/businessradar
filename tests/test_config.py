"""Tests for ConfigManager behavior through its public interface."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestLoadConfigFromEnv:
    """ConfigManager reads configuration from environment variables."""

    def test_reads_api_key_from_env(self):
        from businessradar.config import load_config

        with patch.dict(os.environ, {"BUSINESSRADAR_API_KEY": "sk-test-123"}, clear=False):
            config = load_config()

        assert config.api_key == "sk-test-123"


class TestLoadConfigFromFile:
    """ConfigManager reads configuration from ~/.businessradar/config.yaml."""

    def test_reads_api_key_from_config_file(self, tmp_path: Path):
        from businessradar.config import load_config

        config_dir = tmp_path / ".businessradar"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-from-file-456"}))

        config = load_config(config_path=str(config_file))

        assert config.api_key == "sk-from-file-456"

    def test_reads_model_from_config_file(self, tmp_path: Path):
        from businessradar.config import load_config

        config_dir = tmp_path / ".businessradar"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-x", "llm_model": "claude-sonnet-4-6"}))

        config = load_config(config_path=str(config_file))

        assert config.llm_model == "claude-sonnet-4-6"


class TestCLIPriorityOverrides:
    """CLI arguments override config file and env vars."""

    def test_cli_model_overrides_file(self, tmp_path: Path):
        from businessradar.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-x", "llm_model": "gpt-4o"}))

        config = load_config(
            config_path=str(config_file),
            cli_overrides={"llm_model": "claude-sonnet-4-6"},
        )

        assert config.llm_model == "claude-sonnet-4-6"

    def test_cli_api_key_overrides_env(self):
        from businessradar.config import load_config

        with patch.dict(os.environ, {"BUSINESSRADAR_API_KEY": "sk-env"}, clear=False):
            config = load_config(cli_overrides={"api_key": "sk-cli"})

        assert config.api_key == "sk-cli"

    def test_file_overrides_env(self, tmp_path: Path):
        from businessradar.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": "sk-file"}))

        with patch.dict(os.environ, {"BUSINESSRADAR_API_KEY": "sk-env"}, clear=False):
            config = load_config(config_path=str(config_file))

        assert config.api_key == "sk-file"

    def test_none_cli_overrides_ignored(self):
        from businessradar.config import load_config

        with patch.dict(os.environ, {"BUSINESSRADAR_API_KEY": "sk-env"}, clear=False):
            config = load_config(cli_overrides={"llm_model": None})

        assert config.llm_model == "gpt-4o"  # default, not overridden by None


class TestMissingApiKey:
    """Missing API key produces a clear error."""

    def test_raises_when_no_api_key(self, tmp_path: Path):
        from businessradar.config import ConfigError, load_config

        # No env var, no config file, no CLI override
        with patch.dict(os.environ, {}, clear=True):
            # Remove BUSINESSRADAR_API_KEY if present
            os.environ.pop("BUSINESSRADAR_API_KEY", None)
            empty_config = tmp_path / "config.yaml"
            empty_config.write_text("")

            with pytest.raises(ConfigError, match="API key"):
                load_config(config_path=str(empty_config))

    def test_raises_when_empty_api_key(self, tmp_path: Path):
        from businessradar.config import ConfigError, load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"api_key": ""}))

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("BUSINESSRADAR_API_KEY", None)

            with pytest.raises(ConfigError, match="API key"):
                load_config(config_path=str(config_file))
