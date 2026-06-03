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


class TestRandomUserAgent:
    """Each request uses a random User-Agent from a pool."""

    @patch("businessradar.page_fetcher.random.choice")
    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_uses_random_user_agent(self, mock_urlopen: MagicMock, mock_choice: MagicMock) -> None:
        mock_choice.return_value = "TestAgent/1.0"
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>ok</html>"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = PageFetcher(_make_config(), delay_range=(0, 0))
        fetcher.fetch("https://example.com")

        mock_choice.assert_called_once()
        ua = mock_urlopen.call_args[0][0].get_header("User-agent")
        assert ua == "TestAgent/1.0"


class TestRandomDelay:
    """Requests have random delay to avoid rate-limiting."""

    @patch("businessradar.page_fetcher.time.sleep")
    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_adds_random_delay(self, mock_urlopen: MagicMock, mock_sleep: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>ok</html>"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = PageFetcher(_make_config())
        fetcher.fetch("https://example.com")

        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 1.0 <= delay <= 3.0

    @patch("businessradar.page_fetcher.time.sleep")
    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_delay_respects_configurable_range(self, mock_urlopen: MagicMock, mock_sleep: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>ok</html>"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = PageFetcher(_make_config(), delay_range=(0, 0))
        fetcher.fetch("https://example.com")

        mock_sleep.assert_called_once_with(0.0)


class TestProxySupport:
    """Static requests respect proxy config."""

    @patch("businessradar.page_fetcher.urllib.request.build_opener")
    def test_uses_proxy_when_configured(self, mock_build_opener: MagicMock) -> None:
        mock_opener = MagicMock()
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>proxied</html>"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        config = Config(api_key="test-key", proxy="http://proxy:8080")
        fetcher = PageFetcher(config, delay_range=(0, 0))
        result = fetcher.fetch("https://example.com")

        assert result.used_browser is False
        assert "proxied" in result.html
        # ProxyHandler should be passed to build_opener
        build_args = mock_build_opener.call_args[0]
        assert len(build_args) == 1  # ProxyHandler instance

    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_no_proxy_uses_direct_urlopen(self, mock_urlopen: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b"<html>direct</html>"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        config = Config(api_key="test-key", proxy=None)
        fetcher = PageFetcher(config, delay_range=(0, 0))
        result = fetcher.fetch("https://example.com")

        assert result.used_browser is False
        mock_urlopen.assert_called_once()
