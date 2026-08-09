from dataclasses import dataclass, field
from typing import Protocol

from ai_web_research_agent.domain.research import ExtractionField


class SourceDiscoverer(Protocol):
    """Finds candidate source URLs for a research query.

    Implementations back onto a search engine or a curated index; callers
    only ask for URLs and do not care where they come from.
    """

    async def discover(self, query: str, limit: int) -> list[str]: ...


@dataclass(frozen=True)
class AgentRequest:
    """What the user wants the autonomous agent to research."""

    goal: str
    fields: list[ExtractionField] = field(default_factory=list)
    max_sources: int = 5
    max_retries: int = 2
    candidate_urls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FieldResolution:
    """The final value chosen for one field after comparing sources."""

    field: str
    value: str
    confidence: float | None
    sources: list[str]
    conflicts: int


@dataclass(frozen=True)
class AgentResult:
    """The outcome of a completed autonomous research run."""

    goal: str
    session_id: str | None
    status: str
    summary: str
    findings: list[FieldResolution]
    missing_fields: list[str]
    sources_used: list[str]
    steps: list[str]
