# Crawling Engine

## Purpose

The crawling engine fetches web pages deterministically and extracts useful
content before any AI is involved. It is responsible for responsible crawling:
respecting robots.txt, staying inside the allowed domain, pacing requests and
retrying transient failures.

## Architecture

```
api/crawl.py  (FastAPI route)
   |
   v
services/crawl_service.py  (orchestration + DI wiring)
   |
   +-- services/crawler.py        (crawl loop / coordination)
   |      +-- services/frontier.py         (URL queue + dedup)
   |      +-- services/rate_limiter.py     (per-host request delay)
   |      +-- services/url_normalizer.py   (URL validation/normalization)
   |      +-- infrastructure/http.py       (HTTP fetch + retry)
   |      +-- infrastructure/robots.py     (robots.txt policy)
   |      +-- infrastructure/html_parser.py (BeautifulSoup parsing)
   |
   +-- domain/crawling.py         (models: CrawlRequest, CrawlResult, ...)
```

Dependencies flow inward: the domain layer (`domain/crawling.py`) defines plain
models and knows nothing about HTTP, parsing or FastAPI. Infrastructure
components (httpx, BeautifulSoup) implement concrete behavior and are injected
into the `Crawler` by `crawl_service.py`.

## Data Flow

1. `POST /crawl` accepts a `CrawlRequestSchema` (validated by Pydantic).
2. `crawl_website` reads `Settings`, builds the `HTTPClient`, `RobotsPolicy`,
   `HTMLParser` and `RateLimiter`, and constructs a `Crawler`.
3. `Crawler.crawl` normalizes the start URL, seeds the frontier at depth 0 and
   loops until the frontier is empty or `max_pages` is reached.
4. For each URL it:
   - checks the depth limit,
   - verifies the host is inside the allowed domain,
   - consults `RobotsPolicy.can_fetch` (loading and caching robots.txt per
     origin on first use),
   - waits on the `RateLimiter` to honor the per-host crawl delay,
   - fetches via `HTTPClient` (which retries transient failures),
   - rejects non-HTML responses and HTTP errors,
   - parses HTML into a `PageContent` (title, text, links),
   - enqueues same-domain links discovered on the page at `depth + 1`.

## Key Decisions

- **Default: plain HTTP.** Fetching with httpx is the fast, cheap default.
  Browser rendering is a later phase and will plug in behind the same content
  abstraction.
- **Hand-rolled robots.txt.** Kept async (httpx) with per-origin caching.
  Groups are matched per user-agent (specific group wins over `*`); within a
  group the most specific (longest) rule wins and `Allow` wins ties. If
  robots.txt cannot be fetched the policy fails open.
- **Retries are scoped to transient failures.** Only transport errors and 5xx
  responses are retried with exponential backoff; 4xx responses are returned
  immediately.
- **Rate limiting is per host.** The delay between requests to the same host is
  configurable via `CRAWL_DELAY`, so a crawl stays polite without throttling
  unrelated hosts.
- **Deduplication happens at the frontier.** URLs are normalized (scheme, host
  case, default ports, trailing slashes, fragment removal) before being
  enqueued, so `https://example.com/` and `https://example.com/#top` collapse to
  one page.
- **Failures and skipped URLs are reported, not hidden.** Each processed URL
  produces a `CrawlResult` with a `status` of `success`, `failed` or `skipped`
  and an optional `error`, giving callers a complete picture of the crawl.

## Responsible Crawling

The crawler enforces, from configuration:

| Behavior          | Setting          | Default |
| ----------------- | ---------------- | ------- |
| User agent        | `USER_AGENT`     | `AIWebResearchAgent/0.1` |
| Request timeout   | `REQUEST_TIMEOUT`| `10.0`   |
| Crawl delay       | `CRAWL_DELAY`    | `0.5`    |
| Retry attempts    | `MAX_RETRIES`    | `3`      |
| Max depth/page    | per-request `max_depth` / `max_pages` | `2` / `20` |

robots.txt is always consulted, crawling is confined to the start domain (or an
explicit `allowed_domain`) and every request is paced.

## Tradeoffs

- **Fail-open robots.txt.** If robots.txt is unreachable we crawl rather than
  block; a stricter default (fail-closed) would lose coverage on flaky hosts.
- **Depth-first frontier is FIFO, not priority.** Fine for small focused
  crawls; a page-scoring/priority frontier can replace it later if the research
  agent needs it.
- **Basic robots.txt model.** Wildcard path matching (`*` in paths) is not
  implemented; rules are matched by simple prefix. Sufficient for the current
  scope.
