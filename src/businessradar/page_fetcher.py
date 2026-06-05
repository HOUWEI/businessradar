"""PageFetcher — fetches HTML from URLs with static→browser escalation."""

import random
import time
import urllib.request
from typing import Any

from businessradar.config import Config
from businessradar.models import FetchResult

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[assignment]

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
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None

    def fetch(self, url: str) -> FetchResult:
        """Fetch HTML from url. Try static first; fall back to browser on failure."""
        try:
            html = self._fetch_static(url)
            if not html.strip():
                # Empty response → escalate to browser
                html = self._fetch_browser(url)
                return FetchResult(html=html, used_browser=True)
            return FetchResult(html=html, used_browser=False)
        except Exception:
            html = self._fetch_browser(url)
            return FetchResult(html=html, used_browser=True)

    def screenshot(self) -> bytes:
        """Take a screenshot of the current browser page. Must call _fetch_browser first."""
        if self._page is None:
            raise RuntimeError("No browser page available. Call _fetch_browser first.")
        return self._page.screenshot()

    def close(self) -> None:
        """Shut down the browser and Playwright instance."""
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._page = None

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
        """Browser-based fetch via Playwright for JS-rendered pages."""
        if self._playwright is None:
            if sync_playwright is None:
                raise NotImplementedError(
                    "Playwright is not installed. Run: pip install playwright && playwright install"
                )
            self._playwright = sync_playwright().start()
            launch_opts: dict = {}
            if self._config.proxy:
                launch_opts["proxy"] = {"server": self._config.proxy}
            self._browser = self._playwright.chromium.launch(**launch_opts)
            self._page = self._browser.new_page()

        self._page.goto(url, wait_until="networkidle")
        return self._page.content()
