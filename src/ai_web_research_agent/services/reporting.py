import csv
import io
import json

from ai_web_research_agent.models import ExtractedRecord


def records_to_json(records: list[ExtractedRecord]) -> str:
    payload = [
        {
            "source_url": record.source_url,
            "fields": record.fields,
            "missing_fields": record.missing_fields,
            "confidence": record.confidence,
        }
        for record in records
    ]

    return json.dumps(payload, indent=2)


def records_to_csv(records: list[ExtractedRecord]) -> str:
    field_names = _all_field_names(records)

    header = ["source_url", "confidence"] + field_names + ["missing_fields"]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)

    for record in records:
        row = [
            record.source_url,
            record.confidence if record.confidence is not None else "",
            *[record.fields.get(name, "") for name in field_names],
            ";".join(record.missing_fields),
        ]

        writer.writerow(row)

    return buffer.getvalue()


def records_to_markdown(records: list[ExtractedRecord]) -> str:
    field_names = _all_field_names(records)

    header = ["Source", "Confidence"] + field_names + ["Missing"]

    lines = [
        f"| {' | '.join(header)} |",
        f"| {' | '.join('---' for _ in header)} |",
    ]

    for record in records:
        row = [
            record.source_url,
            f"{record.confidence:.2f}" if record.confidence is not None else "",
            *[record.fields.get(name, "") for name in field_names],
            ", ".join(record.missing_fields),
        ]

        lines.append(f"| {' | '.join(row)} |")

    return "\n".join(lines) + "\n"


def _all_field_names(
    records: list[ExtractedRecord],
) -> list[str]:
    names: list[str] = []

    for record in records:
        for name in record.fields:
            if name not in names:
                names.append(name)

    return names
