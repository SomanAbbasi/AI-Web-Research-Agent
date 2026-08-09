from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FetchedPage:
    """Raw page content independent of the transport that produced it.

    The ``via_browser`` flag tells callers whether the content was rendered
    by a browser or returned by a plain HTTP request.
    """

    url: str
    status_code: int
    html: str
    content_type: str = "text/html"
    via_browser: bool = False


class PageFetcher(Protocol):
    """Fetches a page and returns its HTML regardless of transport.

    Implementations may use plain HTTP or a headless browser; callers do
    not need to know which one produced the content.
    """

    async def fetch(self, url: str) -> FetchedPage: ...
