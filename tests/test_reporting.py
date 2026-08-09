from ai_web_research_agent.models import ExtractedRecord
from ai_web_research_agent.services.reporting import (
    _all_field_names,
    records_to_csv,
    records_to_json,
    records_to_markdown,
)


def make_record(
    fields: dict[str, str],
    *,
    confidence: float | None = 0.8,
    missing: list[str] | None = None,
    url: str = "https://a.com/p",
) -> ExtractedRecord:
    return ExtractedRecord(
        session_id="s1",
        source_url=url,
        fields=fields,
        missing_fields=missing or [],
        has_missing=bool(missing),
        searchable_text="",
        confidence=confidence,
    )


def test_records_to_json_round_trips():
    records = [
        make_record({"name": "Laptop", "price": "$999"}),
    ]

    payload = records_to_json(records)

    assert '"name": "Laptop"' in payload
    assert '"price": "$999"' in payload


def test_records_to_json_includes_confidence_and_missing():
    record = make_record(
        {"name": "Laptop"},
        confidence=None,
        missing=["price"],
    )

    payload = records_to_json([record])

    assert '"confidence": null' in payload
    assert '"missing_fields": [' in payload
    assert '"price"' in payload


def test_records_to_csv_has_header_and_rows():
    records = [
        make_record(
            {"name": "Laptop", "price": "$999"},
            url="https://a.com/laptop",
        ),
        make_record(
            {"name": "Phone"},
            missing=["price"],
            url="https://a.com/phone",
        ),
    ]

    content = records_to_csv(records)

    lines = content.strip().splitlines()

    assert lines[0] == ("source_url,confidence,name,price,missing_fields")
    assert "https://a.com/laptop,0.8,Laptop,$999," in lines[1]
    assert "https://a.com/phone,0.8,Phone,,price" in lines[2]


def test_records_to_markdown_renders_table():
    records = [
        make_record({"name": "Laptop"}, url="https://a.com/laptop"),
    ]

    content = records_to_markdown(records)

    assert "| Source | Confidence | name | Missing |" in content
    assert "| --- |" in content
    assert "| https://a.com/laptop | 0.80 | Laptop |  |" in content


def test_all_field_names_ordered_by_appearance():
    records = [
        make_record({"name": "A", "price": "$1"}),
        make_record({"price": "$2", "color": "red"}),
    ]

    assert _all_field_names(records) == ["name", "price", "color"]


def test_records_to_csv_handles_empty_list():
    assert records_to_csv([]).strip().splitlines() == ["source_url,confidence,missing_fields"]
