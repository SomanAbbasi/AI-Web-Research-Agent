from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        default="running",
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    pages: Mapped[list["CrawledPage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    records: Mapped[list["ExtractedRecord"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    sources: Mapped[list["Source"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class Source(Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "url",
            name="uq_source_session_url",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    url: Mapped[str] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )

    session: Mapped[ResearchSession] = relationship(
        back_populates="sources",
    )


class CrawledPage(Base):
    __tablename__ = "crawled_pages"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "url",
            name="uq_page_session_url",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int] = mapped_column(Integer)
    via_browser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )

    session: Mapped[ResearchSession] = relationship(
        back_populates="pages",
    )


class ExtractedRecord(Base):
    __tablename__ = "extracted_records"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "source_url",
            name="uq_record_session_url",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("research_sessions.id"))
    source_url: Mapped[str] = mapped_column(Text)
    fields: Mapped[dict[str, str]] = mapped_column(JSON)
    missing_fields: Mapped[list[str]] = mapped_column(JSON)
    has_missing: Mapped[bool] = mapped_column(Boolean, default=False)
    searchable_text: Mapped[str] = mapped_column(
        Text,
        default="",
    )
    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now,
    )

    session: Mapped[ResearchSession] = relationship(
        back_populates="records",
    )
