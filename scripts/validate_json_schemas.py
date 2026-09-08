"""Validate the event contracts against JSON Schema Draft 2020-12."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


SCHEMAS_DIRECTORY = Path("contracts/events")
EXPECTED_EVENT_TYPES = {
    "processing.requested",
    "processing.started",
    "processing.progressed",
    "processing.completed",
    "processing.failed",
}
ENVELOPE_FIELDS = {
    "event_id",
    "event_type",
    "event_version",
    "occurred_at",
    "correlation_id",
    "data",
}


def main() -> None:
    schema_paths = sorted(SCHEMAS_DIRECTORY.glob("*.schema.json"))
    if not schema_paths:
        raise SystemExit("Nenhum JSON Schema de evento foi encontrado.")

    event_types: set[str] = set()
    for schema_path in schema_paths:
        with schema_path.open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)

        Draft202012Validator.check_schema(schema)
        required_fields = set(schema.get("required", []))
        missing_fields = ENVELOPE_FIELDS - required_fields
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise SystemExit(f"{schema_path}: campos obrigatórios ausentes: {missing}")

        event_type = schema.get("properties", {}).get("event_type", {}).get("const")
        if not event_type:
            raise SystemExit(f"{schema_path}: event_type.const não foi definido")
        event_types.add(event_type)

    if event_types != EXPECTED_EVENT_TYPES:
        missing = EXPECTED_EVENT_TYPES - event_types
        unexpected = event_types - EXPECTED_EVENT_TYPES
        raise SystemExit(
            f"Conjunto de eventos inválido; ausentes={sorted(missing)}, "
            f"inesperados={sorted(unexpected)}"
        )

    print(f"{len(schema_paths)} JSON Schemas válidos.")


if __name__ == "__main__":
    main()
