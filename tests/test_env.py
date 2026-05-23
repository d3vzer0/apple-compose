from pathlib import Path

import pytest

from apple_compose.env import parse_env_file, service_env
from apple_compose.errors import InterpolationError
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
    copy_sample(tmp_path, "env", "service.env")

    result = service_env(
        {"B": "inline", "C": "${BASE}"},
        "service.env",
        base_dir=tmp_path,
        base_environment={"BASE": "value"},
    )

    assert result == {"A": "file", "B": "inline", "C": "${BASE}"}


def test_service_env_list_reads_base_environment(tmp_path: Path) -> None:
    result = service_env(
        ["A=inline", "FROM_BASE"],
        None,
        base_dir=tmp_path,
        base_environment={"FROM_BASE": "value"},
    )

    assert result == {"A": "inline", "FROM_BASE": "value"}
