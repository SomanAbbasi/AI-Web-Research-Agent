from ai_web_research_agent.models import (
    ExtractedRecord,
)


def make_record(
    session_id: str,
    url: str,
    *,
    fields: dict[str, str] | None = None,
    confidence: float | None = 1.0,
    has_missing: bool = False,
    missing_fields: list[str] | None = None,
) -> ExtractedRecord:
    return ExtractedRecord(
        session_id=session_id,
        source_url=url,
        fields=fields or {"name": url},
        missing_fields=missing_fields or [],
        has_missing=has_missing,
        searchable_text=" ".join((fields or {}).values()),
        confidence=confidence,
    )


async def test_create_and_get_session(repository):
    created = await repository.create_session("research the market")

    assert created.goal == "research the market"
    assert created.status == "running"
    assert created.id

    fetched = await repository.get_session(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.goal == "research the market"


async def test_get_session_returns_none_for_missing(repository):
    assert await repository.get_session("does-not-exist") is None


async def test_complete_session(repository):
    session = await repository.create_session("goal")

    completed = await repository.complete_session(session.id)

    assert completed is not None
    assert completed.status == "completed"
    assert completed.completed_at is not None


async def test_complete_missing_session_returns_none(repository):
    assert await repository.complete_session("does-not-exist") is None


async def test_list_sessions_orders_by_creation(repository):
    first = await repository.create_session("first")
    second = await repository.create_session("second")

    sessions = await repository.list_sessions()

    ids = [session.id for session in sessions]

    assert ids == [second.id, first.id]


async def test_add_source_is_deduplicated(repository):
    session = await repository.create_session("goal")

    assert await repository.add_source(session.id, "https://a.com") is True
    assert await repository.add_source(session.id, "https://a.com") is False


async def test_add_page_is_deduplicated(repository):
    session = await repository.create_session("goal")

    added = await repository.add_page(
        session.id,
        url="https://a.com/page",
        title="Page",
        text="content",
        status_code=200,
        via_browser=False,
    )

    assert added is True

    duplicate = await repository.add_page(
        session.id,
        url="https://a.com/page",
        title="Page",
        text="content",
        status_code=200,
        via_browser=False,
    )

    assert duplicate is False


async def test_add_record_is_deduplicated_by_url(repository):
    session = await repository.create_session("goal")

    record = make_record(session.id, "https://a.com/p")

    assert await repository.add_record(session.id, record) is True

    duplicate = make_record(session.id, "https://a.com/p")

    assert await repository.add_record(session.id, duplicate) is False


async def test_list_records_returns_total_and_paginates(repository):
    session = await repository.create_session("goal")

    for index in range(5):
        await repository.add_record(
            session.id,
            make_record(
                session.id,
                f"https://a.com/{index}",
                fields={"name": f"item-{index}"},
            ),
        )

    records, total = await repository.list_records(
        session.id,
        limit=2,
        offset=0,
    )

    assert total == 5
    assert len(records) == 2


async def test_list_records_filters_by_confidence(repository):
    session = await repository.create_session("goal")

    await repository.add_record(
        session.id,
        make_record(
            session.id,
            "https://a.com/low",
            confidence=0.4,
        ),
    )
    await repository.add_record(
        session.id,
        make_record(
            session.id,
            "https://a.com/high",
            confidence=0.9,
        ),
    )

    records, total = await repository.list_records(
        session.id,
        min_confidence=0.5,
    )

    assert total == 1
    assert records[0].source_url == "https://a.com/high"


async def test_list_records_filters_by_search(repository):
    session = await repository.create_session("goal")

    await repository.add_record(
        session.id,
        make_record(
            session.id,
            "https://a.com/laptop",
            fields={"name": "MacBook Pro"},
        ),
    )
    await repository.add_record(
        session.id,
        make_record(
            session.id,
            "https://a.com/phone",
            fields={"name": "Pixel 9"},
        ),
    )

    records, total = await repository.list_records(
        session.id,
        search="MacBook",
    )

    assert total == 1
    assert records[0].source_url == "https://a.com/laptop"


async def test_list_records_filters_by_missing(repository):
    session = await repository.create_session("goal")

    await repository.add_record(
        session.id,
        make_record(
            session.id,
            "https://a.com/full",
            has_missing=False,
        ),
    )
    await repository.add_record(
        session.id,
        make_record(
            session.id,
            "https://a.com/incomplete",
            has_missing=True,
            missing_fields=["price"],
        ),
    )

    records, total = await repository.list_records(
        session.id,
        include_missing=True,
    )

    assert total == 1
    assert records[0].source_url == "https://a.com/incomplete"


async def test_get_record(repository):
    session = await repository.create_session("goal")
    record = make_record(session.id, "https://a.com/p")

    await repository.add_record(session.id, record)

    records, _total = await repository.list_records(session.id)

    fetched = await repository.get_record(records[0].id)

    assert fetched is not None
    assert fetched.source_url == "https://a.com/p"
