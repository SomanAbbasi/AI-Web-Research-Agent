from dataclasses import dataclass, field
from enum import Enum


class CrawlStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class CrawlRequest:
    start_url: str
    max_depth: int = 2
    max_pages: int = 50
    allowed_domain: str | None = None


@dataclass(frozen=True)
class PageLink:
    url: str
    text: str = ""


@dataclass
class PageContent:
    url: str
    status_code: int
    title: str | None
    text: str
    links: list[PageLink] = field(default_factory=list)
    via_browser: bool = False


@dataclass
class CrawlResult:
    url: str
    status: CrawlStatus
    page: PageContent | None = None
    error: str | None = None
