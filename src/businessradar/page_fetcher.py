"""PageFetcher — fetches HTML from URLs with static→browser escalation."""

import random
import time
import urllib.request

from businessradar.config import Config
from businessradar.models import FetchResult

# Pool of realistic User-Agent strings for anti-detection rotation
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
]


class PageFetcher:
    """Fetch page HTML, escalating from static HTTP to browser if needed."""

    def __init__(
        self,
        config: Config,
        delay_range: tuple[float, float] = (1.0, 3.0),
    ) -> None:
        self._config = config
        self._delay_range = delay_range

    def fetch(self, url: str) -> FetchResult:
        """Fetch HTML from url. Try static first; fall back to browser on failure."""
        try:
            html = self._fetch_static(url)
            return FetchResult(html=html, used_browser=False)
        except Exception:
            html = self._fetch_browser(url)
            return FetchResult(html=html, used_browser=True)

    def _fetch_static(self, url: str) -> str:
        """Static HTTP GET via urllib with random UA and delay."""
        time.sleep(random.uniform(*self._delay_range))
        req = urllib.request.Request(url, headers={"User-Agent": random.choice(_USER_AGENTS)})

        if self._config.proxy:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": self._config.proxy, "https": self._config.proxy})
            )
            with opener.open(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        else:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")

    def _fetch_browser(self, url: str) -> str:
        """Browser-based fetch via Playwright (placeholder for Issue #5+)."""
        raise NotImplementedError("Browser fetch not yet implemented")
