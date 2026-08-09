# Data Management & Reporting

Phase 5 adds durable, queryable storage for research results and report
export. Data access is kept behind repositories and services so the rest of
the application never talks to SQLAlchemy sessions directly.

## Persistence

- **SQLAlchemy 2.0 async** with two dialects:
  - `postgresql+asyncpg` for production.
  - `sqlite+aiosqlite` for local development and tests.
- Selected via the `DATABASE_URL` setting
  (default: `sqlite+aiosqlite:///./research.db`).
- Tables are created on startup by the FastAPI lifespan hook if they do not
  exist. No migration tooling is used yet.

### Models

Defined in `src/ai_web_research_agent/models/`:

- `ResearchSession` — a unit of research with a goal, status
  (`running`/`completed`/`failed`) and timestamps.
- `Source` — a discovered URL, deduplicated per session.
- `CrawledPage` — a fetched page with title, text, status code and whether it
  was rendered in a browser, deduplicated per session.
- `ExtractedRecord` — extracted fields, missing-field list, confidence,
  `has_missing` flag and a denormalized `searchable_text` column for search.

Pages, sources and records are deduplicated by `(session_id, url)` via unique
constraints; inserts that violate the constraint are treated as no-ops.

## Repository

`infrastructure/persistence/repository.py` exposes `ResearchRepository`, which
owns all query logic:

- `create_session` / `get_session` / `list_sessions` / `complete_session`
- `add_source` / `add_page` / `add_record` (deduplicated)
- `list_records(session_id, min_confidence, search, include_missing, limit,
  offset)` — returns `(records, total)` for pagination
- `get_record`

## Services

`services/research_service.py` is the application-facing facade. It maps
domain extraction records into persisted models (setting `searchable_text` and
`has_missing`) and forwards filter/pagination options to the repository. The
service holds a configurable session factory so tests can inject an isolated
database.

## Reporting

`services/reporting.py` renders a list of records into:

- **JSON** — array of objects with `source_url`, `fields`, `missing_fields`,
  `confidence`.
- **CSV** — a header row of unioned field names; missing fields column is
  semicolon-joined.
- **Markdown** — a table with the same columns.

## API

| Method | Path                             | Description                          |
| ------ | -------------------------------- | ------------------------------------ |
| POST   | `/research/sessions`             | Create a research session            |
| GET    | `/research/sessions`             | List sessions (newest first)         |
| GET    | `/research/sessions/{id}`        | Get a session                        |
| GET    | `/research/sessions/{id}/records`| List records with filters/pagination |
| GET    | `/research/sessions/{id}/report` | Export records (`json`/`csv`/`markdown`) |

Record listing supports `min_confidence`, `search`, `include_missing`,
`limit` (1–100) and `offset`.

## Testing

Repository and service tests use a per-test file-backed SQLite database so
each test starts from an empty schema. API tests run through
`TestClient(app)` as a context manager so the lifespan initializes tables.
`DATABASE_URL` defaults to an in-memory SQLite database in the test suite.
