from types import TracebackType
from typing import Self

from playwright.async_api import (
    Browser,
    Playwright,
    async_playwright,
)
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from ai_web_research_agent.domain.fetching import FetchedPage


class BrowserPageFetcher:
    """Fetches pages by rendering them in a headless browser.

    A single browser instance is reused across fetches and released when
    the fetcher is used as an async context manager.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        render_delay: float = 1.0,
        user_agent: str = "AIWebResearchAgent/0.1",
        browser_type: str = "chromium",
    ) -> None:
        self._timeout = timeout
        self._render_delay = render_delay
        self._user_agent = user_agent
        self._browser_type = browser_type
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> Self:
        await self._ensure_started()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None

        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    async def fetch(self, url: str) -> FetchedPage:
        await self._ensure_started()

        if self._browser is None:
            raise RuntimeError("Browser failed to start")

        page = await self._browser.new_page(
            user_agent=self._user_agent,
        )

        try:
            response = await page.goto(
                url,
                timeout=int(self._timeout * 1000),
                wait_until="domcontentloaded",
            )

            if self._render_delay > 0:
                await page.wait_for_timeout(int(self._render_delay * 1000))

            html = await page.content()
            status_code = response.status if response is not None else 200

            return FetchedPage(
                url=page.url,
                status_code=status_code,
                html=html,
                via_browser=True,
            )
        except PlaywrightTimeoutError:
            # A timeout can still leave a partially rendered DOM; return it.
            html = await page.content()

            return FetchedPage(
                url=page.url,
                status_code=200,
                html=html,
                via_browser=True,
            )
        finally:
            await page.close()

    async def _ensure_started(self) -> None:
        if self._browser is not None:
            return

        self._playwright = await async_playwright().start()

        factory = getattr(self._playwright, self._browser_type)

        self._browser = await factory.launch(headless=True)
