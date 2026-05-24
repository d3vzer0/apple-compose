from pathlib import Path

import pytest

from apple_compose.env import parse_env_file
from apple_compose.errors import InterpolationError
from apple_compose.models import ServiceConfig
from conftest import copy_sample


def test_parse_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING", raising=False)
    env_file = copy_sample(tmp_path, "env", "dotenv.env", name=".env")

    assert parse_env_file(env_file) == {
        "A": "one",
        "B": "two words",
        "C": "three",
        "D": "one",
        "E": "fallback",
        "EMPTY": "",
    }


def test_parse_env_file_missing_required(tmp_path: Path) -> None:
    with pytest.raises(InterpolationError):
        parse_env_file(tmp_path / "missing.env", required=True)


def test_service_env_precedence(tmp_path: Path) -> None:
    service = ServiceConfig.model_validate({"image": "nginx", "environment": {"B": "inline", "C": "${BASE}"}})

    assert service.environment_values({"BASE": "value"}) == {"B": "inline", "C": "${BASE}"}


def test_service_env_list_reads_base_environment(tmp_path: Path) -> None:
    service = ServiceConfig.model_validate(
        {"image": "nginx", "environment": ["A=inline", "FROM_BASE"]}
    )

    assert service.environment_values({"FROM_BASE": "value"}) == {
        "A": "inline",
        "FROM_BASE": "value",
    }
