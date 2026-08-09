from types import TracebackType
from typing import Self

import httpx


class HTTPClient:
    """Reusable asynchronous HTTP client."""

    def __init__(
        self,
        timeout: float = 10.0,
        user_agent: str = "AIWebResearchAgent/0.1",
    ) -> None:
        self._timeout = timeout
        self._user_agent = user_agent
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
            raise RuntimeError(
                "HTTPClient must be used as an async context manager"
            )

        return await self._client.get(url)