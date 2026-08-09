# AI Web Research Agent

Production-inspired AI-powered Web Research Agent.

This project is being developed phase by phase.

## Current Phase

Phase 3 — Browser Automation

## Features

- FastAPI application
- Configuration management
- Structured logging
- Health endpoint
- Pydantic validation
- Pytest test suite
- Ruff linting
- URL normalization and validation
- URL frontier with deduplication
- robots.txt parsing with user-agent matching
- Per-host rate limiting
- Retry handling with exponential backoff
- HTML parsing and link extraction
- Same-domain crawling with depth and page limits
- Transport-agnostic page fetching (HTTP default, Playwright fallback)
- JavaScript rendering for thin HTTP content

## Project Layout

```
src/ai_web_research_agent/
├── api/            # HTTP routes
├── config/         # Settings (env-driven)
├── core/           # Cross-cutting concerns (logging)
├── domain/         # Business models and interfaces
├── infrastructure/ # External systems (HTTP, parsing, robots)
├── models/         # Persistence models (later phases)
├── schemas/        # Pydantic request/response schemas
├── services/       # Application services and orchestration
└── utils/          # Small reusable utilities
```

## Local Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies with uv:

```bash
uv sync
```

Copy the environment template and adjust as needed:

```bash
cp .env.example .env
```

Run the API:

```bash
uv run uvicorn ai_web_research_agent.app:app --reload
```

## Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

## Documentation

- [Crawling Engine](docs/crawling.md)
- [Browser Automation](docs/browser-automation.md)
