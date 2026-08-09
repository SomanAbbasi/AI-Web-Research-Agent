# Browser Automation

## Purpose

Some pages render their meaningful content with JavaScript and return only a
skeleton over plain HTTP. The browser automation layer re-renders those pages
in a headless browser so the crawler still gets usable content. Plain HTTP
remains the default because it is faster and cheaper.

## Architecture

```
services/crawler.py
   |
   +-- PageFetcher (Protocol, domain/fetching.py)   <-- the seam
          |
          +-- HybridPageFetcher (services/fetching.py)
          |      |
          |      +-- HttpPageFetcher  (infrastructure/http.py)   httpx
          |      +-- BrowserPageFetcher (infrastructure/browser.py)  Playwright
          |
          +-- FetchedPage (domain/fetching.py)
```

`FetchedPage` carries the URL, status code, HTML, content type and a
`via_browser` flag. Nothing downstream cares which transport produced the
content; `PageContent.via_browser` records it for callers that want to know.

## Data Flow

1. `HybridPageFetcher.fetch` calls the HTTP fetcher first.
2. `is_page_complete` measures the visible text of the returned HTML
   (`MIN_VISIBLE_TEXT`, default 200 chars, excluding script/style blocks).
3. If the content looks complete, the HTTP page is returned as-is.
4. If it looks incomplete and a browser fetcher is available
   (`USE_BROWSER=true`), the page is re-rendered with Playwright.
5. If rendering fails or times out, the original HTTP content is returned
   rather than failing the crawl.

## Browser Fetching

`BrowserPageFetcher` uses Playwright's async API:

- one Chromium browser instance is reused across fetches and released on
  `aclose()` (it is usable as an async context manager);
- each page navigates with `domcontentloaded`, waits `BROWSER_RENDER_DELAY`
  (default 1s) for JavaScript to settle, then captures the rendered DOM;
- a navigation timeout (`BROWSER_TIMEOUT`) returns the partially rendered DOM
  instead of raising, so content is not lost.

## Configuration

| Setting                 | Default  | Purpose                             |
| ----------------------- | -------- | ----------------------------------- |
| `USE_BROWSER`           | `false`  | Enable browser fallback (opt-in)    |
| `BROWSER_TIMEOUT`       | `30.0`   | Navigation timeout in seconds       |
| `BROWSER_RENDER_DELAY`  | `1.0`    | Settle delay after load, seconds    |
| `MIN_VISIBLE_TEXT`      | `200`    | Text length threshold for "complete"|

## Tradeoffs

- **Browser fallback is opt-in.** HTTP stays the default; teams that don't
  need JS rendering avoid the Playwright overhead.
- **Heuristic, not proof.** A short text threshold is a cheap proxy for
  "JS-rendered". It can trigger a wasted render on genuinely short pages and
  miss pages that render to empty DOM. Refinements (e.g., detecting SPA root
  placeholders) can be added to `is_page_complete` later.
- **Per-fetch cost.** Rendering is expensive; the hybrid fetcher only pays it
  when the HTTP result looks incomplete.

## Testing Note

Unit tests cover the decision and fallback logic with fake fetchers and do not
launch a real browser. To exercise the real Chromium integration locally, run
`uv run playwright install chromium` first.
