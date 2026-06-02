"""Shared test fixtures for BusinessRadar."""

import pytest

from businessradar.config import Config
from businessradar.models import PageAnalysis


@pytest.fixture
def test_config() -> Config:
    return Config(api_key="test-key", llm_model="gpt-4o")


@pytest.fixture
def sample_analysis() -> PageAnalysis:
    return PageAnalysis(
        list_item_selector="div.vT-s-result",
        fields={"title": "a.title", "date": "span.date", "link": "a.title@href"},
        page_type="static",
    )
