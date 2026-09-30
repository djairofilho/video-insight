import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from processing_service.config import Settings

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "events"


@pytest.fixture
def settings() -> Settings:
    return Settings(worker_id="worker-test", consumer_enabled=False, rabbitmq_reconnect_seconds=0)


@pytest.fixture(scope="session")
def validate_event() -> Callable[[dict[str, Any]], None]:
    validators = {}
    for path in CONTRACTS.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        event_type = schema["properties"]["event_type"]["const"]
        validators[event_type] = Draft202012Validator(
            schema, format_checker=Draft202012Validator.FORMAT_CHECKER
        )

    def validate(payload: dict[str, Any]) -> None:
        validators[payload["event_type"]].validate(payload)

    return validate

