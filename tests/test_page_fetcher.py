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


class TestBrowserFetch:
    """Playwright browser fetch via sync_playwright."""

    @patch("businessradar.page_fetcher.sync_playwright")
    def test_browser_fetch_returns_html(self, mock_pw_func: MagicMock) -> None:
        mock_pw = MagicMock()
        mock_pw_func.return_value.start.return_value = mock_pw

        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_page.content.return_value = "<html><body>Dynamic</body></html>"
        mock_browser.new_page.return_value = mock_page

        fetcher = PageFetcher(_make_config(), delay_range=(0, 0))
        html = fetcher._fetch_browser("https://example.com")

        assert "Dynamic" in html
        mock_page.goto.assert_called_once_with("https://example.com", wait_until="networkidle")

    @patch("businessradar.page_fetcher.sync_playwright")
    def test_screenshot_captures_page(self, mock_pw_func: MagicMock) -> None:
        mock_pw = MagicMock()
        mock_pw_func.return_value.start.return_value = mock_pw

        mock_browser = MagicMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_page = MagicMock()
        mock_page.screenshot.return_value = b"\x89PNG fake screenshot data"
        mock_browser.new_page.return_value = mock_page

        fetcher = PageFetcher(_make_config(), delay_range=(0, 0))
        fetcher._fetch_browser("https://example.com")  # init browser
        screenshot = fetcher.screenshot()

        assert screenshot == b"\x89PNG fake screenshot data"
        mock_page.screenshot.assert_called_once()

    def test_close_shuts_down_browser(self) -> None:
        fetcher = PageFetcher(_make_config())
        mock_browser = MagicMock()
        fetcher._browser = mock_browser

        fetcher.close()

        mock_browser.close.assert_called_once()
        assert fetcher._browser is None


class TestEscalationTriggers:
    """Static requests that should trigger browser escalation."""

    @patch.object(PageFetcher, "_fetch_browser", return_value="<html>dynamic</html>")
    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_escalates_on_403(self, mock_urlopen: MagicMock, mock_browser: MagicMock) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://example.com", code=403, msg="Forbidden",
            hdrs=None, fp=None,
        )

        fetcher = PageFetcher(_make_config(), delay_range=(0, 0))
        result = fetcher.fetch("https://example.com")

        assert result.used_browser is True
        mock_browser.assert_called_once()

    @patch.object(PageFetcher, "_fetch_browser", return_value="<html>dynamic</html>")
    @patch("businessradar.page_fetcher.urllib.request.urlopen")
    def test_escalates_on_empty_response(self, mock_urlopen: MagicMock, mock_browser: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        fetcher = PageFetcher(_make_config(), delay_range=(0, 0))
        result = fetcher.fetch("https://example.com")

        assert result.used_browser is True
        mock_browser.assert_called_once()
