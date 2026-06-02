"""Tests for PageFetcher — HTTP page fetching with static→browser escalation."""

from unittest.mock import MagicMock, patch

from businessradar.config import Config
from businessradar.page_fetcher import PageFetcher


def _make_config() -> Config:
    """Create a minimal Config for testing."""
    return Config(api_key="test-key")


class TestPageFetcherStatic:
    """Static HTTP request succeeds → FetchResult with HTML."""

    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_static_request_returns_html(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html><body>List Page</body></html>"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = PageFetcher(_make_config())
        result = fetcher.fetch("https://example.com/list")

        assert result.used_browser is False
        assert "List Page" in result.html


class TestPageFetcherBrowserEscalation:
    """Static request fails → auto-upgrade to browser mode."""

    @patch.object(PageFetcher, "_fetch_browser", return_value="<html>dynamic</html>")
    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_escalates_to_browser_on_static_failure(
        self, mock_urlopen: MagicMock, mock_browser: MagicMock
    ) -> None:
        mock_urlopen.side_effect = Exception("Connection refused")

        fetcher = PageFetcher(_make_config())
        result = fetcher.fetch("https://example.com/list")

        assert result.used_browser is True
        assert "dynamic" in result.html
        mock_browser.assert_called_once_with("https://example.com/list")
