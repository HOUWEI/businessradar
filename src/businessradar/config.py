"""Configuration management with three-tier priority: CLI > config file > env vars."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel

DEFAULT_CONFIG_PATH = Path.home() / ".businessradar" / "config.yaml"


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


class Config(BaseModel):
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    api_key: str = ""
    llm_base_url: str | None = None
    max_retries: int = 10
    max_pages: int = 50
    proxy: str | None = None


def _read_config_file(config_path: Path | None = None) -> dict:
    """Read YAML config file if it exists."""
    path = config_path or DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    return {}


def load_config(
    cli_overrides: dict | None = None,
    config_path: str | None = None,
) -> Config:
    """Load config with priority: cli_overrides > config file > env vars."""
    values: dict = {}

    # Tier 3: environment variables
    env_api_key = os.environ.get("BUSINESSRADAR_API_KEY")
    if env_api_key:
        values["api_key"] = env_api_key

    # Tier 2: config file
    file_path = Path(config_path) if config_path else None
    file_values = _read_config_file(file_path)
    values.update(file_values)

    # Tier 1: CLI overrides (highest priority)
    if cli_overrides:
        values.update({k: v for k, v in cli_overrides.items() if v is not None})

    config = Config(**values)

    if not config.api_key:
        raise ConfigError(
            "API key is required. Set it via BUSINESSRADAR_API_KEY env var, "
            "config file (~/.businessradar/config.yaml), or --api-key CLI argument."
        )

    return config
