from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractionField:
    """A single piece of information the user wants extracted."""

    name: str
    description: str = ""


@dataclass(frozen=True)
class ResearchRequest:
    """What the user wants to learn from a single page."""

    goal: str
    source_url: str
    fields: list[ExtractionField] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedRecord:
    """Structured data extracted from one source page."""

    source_url: str
    fields: dict[str, str] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    confidence: float | None = None
