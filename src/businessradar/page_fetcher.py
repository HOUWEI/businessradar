"""PageFetcher — fetches HTML from URLs with static→browser escalation."""

import urllib.request

from businessradar.config import Config
from businessradar.models import FetchResult


class PageFetcher:
    """Fetch page HTML, escalating from static HTTP to browser if needed."""

    def __init__(self, config: Config) -> None:
        self._config = config

    def fetch(self, url: str) -> FetchResult:
        """Fetch HTML from url. Try static first; fall back to browser on failure."""
        try:
            html = self._fetch_static(url)
            return FetchResult(html=html, used_browser=False)
        except Exception:
            html = self._fetch_browser(url)
            return FetchResult(html=html, used_browser=True)

    def _fetch_static(self, url: str) -> str:
        """Static HTTP GET via urllib."""
        req = urllib.request.Request(url, headers={"User-Agent": self._user_agent()})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _fetch_browser(self, url: str) -> str:
        """Browser-based fetch via Playwright (placeholder for Issue #5+)."""
        raise NotImplementedError("Browser fetch not yet implemented")

    @staticmethod
    def _user_agent() -> str:
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        )
