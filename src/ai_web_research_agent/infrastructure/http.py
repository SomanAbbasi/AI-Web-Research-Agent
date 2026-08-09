import asyncio
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Self

import httpx

from ai_web_research_agent.domain.fetching import FetchedPage


class RetryPolicy:
    """How many attempts a request may make and the delay between them.

    Attempts are retried on transient failures: transport errors (timeouts,
    connection problems) and 5xx server responses.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        backoff: float = 0.5,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.max_attempts = max_attempts
        self.backoff = backoff

    def delay_for(self, attempt: int) -> float:
        """Exponential backoff for the given 1-based attempt number."""
        return self.backoff * float(2 ** (attempt - 1))


class HTTPClient:
    """Reusable asynchronous HTTP client with retry support."""

    def __init__(
        self,
        timeout: float = 10.0,
        user_agent: str = "AIWebResearchAgent/0.1",
        retry_policy: RetryPolicy | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent
        self._retry_policy = retry_policy or RetryPolicy()
        self._sleeper = sleeper
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
            headers={
                "User-Agent": self._user_agent,
            },
            follow_redirects=True,
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get(self, url: str) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("HTTPClient must be used as an async context manager")

        attempt = 1

        while True:
            try:
                response = await self._client.get(url)

                if response.status_code >= 500 and attempt < self._retry_policy.max_attempts:
                    await self._backoff(attempt)
                    attempt += 1
                    continue

                return response
            except httpx.TransportError:
                if attempt >= self._retry_policy.max_attempts:
                    raise

                await self._backoff(attempt)
                attempt += 1

    async def _backoff(self, attempt: int) -> None:
        await self._sleeper(self._retry_policy.delay_for(attempt))


class HttpPageFetcher:
    """Fetches pages over plain HTTP."""

    def __init__(self, http_client: HTTPClient) -> None:
        self._http_client = http_client

    async def fetch(self, url: str) -> FetchedPage:
        response = await self._http_client.get(url)

        return FetchedPage(
            url=str(response.url),
            status_code=response.status_code,
            html=response.text,
            content_type=response.headers.get("content-type", "text/html"),
        )
