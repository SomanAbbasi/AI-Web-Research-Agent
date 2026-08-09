# Autonomous AI Research Agent

Phase 6 ties the previous phases together into a single autonomous loop. Given
a goal and the fields to extract, the agent plans queries, discovers sources,
extracts data, validates coverage, retries on missing information, resolves
conflicts across sources, and produces a final report — persisting everything
along the way.

## Architecture

The agent is a **deterministic state machine** orchestrated by
`AgentOrchestrator` in `services/agent.py`. An explicit graph framework (e.g.
LangGraph) was deliberately avoided: the control flow is a single loop with
one decision point, so a hand-written orchestrator is easier to follow and
test. Swapping in a graph later would not change the domain or service
contracts.

### Stages

1. **Plan** — an LLM decomposes the goal into up to three search queries.
   Invalid or empty LLM output falls back to a deterministic query built from
   the goal plus the still-missing field names.
2. **Discover** — queries are turned into source URLs by a `SourceDiscoverer`.
   URLs are normalized and deduplicated; the batch is capped at `max_sources`.
   The default implementation queries DuckDuckGo's HTML endpoint
   (`infrastructure/search.py`). Candidate URLs supplied by the caller are
   always used first.
3. **Select** — the orchestrator decides the next action. While fields are
   missing it extracts the next pending source; once every field has a value
   it stops extracting immediately. When the queue is empty it checks whether
   a retry round is available.
4. **Crawl / render decision** — each source is fetched through the existing
   hybrid fetcher (HTTP first, browser render only when the HTTP content looks
   incomplete). Page and record are persisted to the research session.
5. **Extract** — the LLM extracts the requested fields from the page text.
   A failing source is skipped and never aborts the run.
6. **Validate** — the agent recomputes missing fields from all records seen so
   far.
7. **Missing-info retry** — if fields are still missing and retry rounds
   remain, the agent plans again (now targeting the missing fields), discovers
   new sources, and continues. Discovery that returns nothing new ends the
   loop instead of spinning.
8. **Compare / resolve** — for each field the candidates from every source are
   collected. The winning value is the most common one, with a tie broken by
   the highest per-source confidence. Conflicts are counted and reported.
9. **Synthesize** — an LLM writes a short narrative summary of the resolved
   findings. On failure the agent returns a deterministic summary.
10. **Report** — an `AgentResult` with status, summary, per-field resolutions,
    missing fields, sources used and the step log. The research session is
    marked `completed`.

### Failure handling

- Extraction errors on an individual source are logged and skipped.
- LLM planning/synthesis failures fall back to deterministic behaviour.
- A repository failure marks the session `failed` and re-raises.

## Persistence

When a `ResearchRepository` is provided, each run creates a `ResearchSession`
and stores discovered sources, crawled pages and extracted records, then marks
the session completed. This reuses the Phase 5 data layer unchanged.

## API

| Method | Path             | Description                        |
| ------ | ---------------- | ---------------------------------- |
| POST   | `/research/agent`| Run the autonomous research agent  |

Request body:

```json
{
  "goal": "Find laptop prices",
  "fields": [
    {"name": "name", "description": "Product name"},
    {"name": "price", "description": "Price in USD"}
  ],
  "max_sources": 5,
  "max_retries": 2,
  "candidate_urls": ["https://example.com/laptop"]
}
```

Response: `status`, `session_id`, `summary`, `findings` (field, value,
confidence, sources, conflicts), `missing_fields`, `sources_used`, `steps`.

The endpoint runs synchronously; a job/queue-based execution model is future
work for long-running research.

## Configuration

The agent uses the existing LLM and crawling settings:

- `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_MODEL` / `LLM_MAX_CONTEXT`
- `USER_AGENT` / `REQUEST_TIMEOUT` / `MAX_RETRIES`
- `USE_BROWSER` / `BROWSER_TIMEOUT` / `MIN_VISIBLE_TEXT`
- `DATABASE_URL`

## Testing

`tests/test_agent.py` covers planning (queries and fallbacks), tool selection
(early stop when complete), missing-info retry, incomplete research, the
no-new-sources guard, persistence, and conflict resolution (majority wins,
confidence tie-break). `tests/test_agent_api.py` exercises the endpoint
end-to-end, and `tests/test_search.py` covers result parsing without network
access.
