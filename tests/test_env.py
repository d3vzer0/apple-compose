from pathlib import Path

import pytest

from apple_compose.env import interpolate_string, parse_env_file
from apple_compose.errors import InterpolationError
from apple_compose.models import ComposeConfig, ServiceConfig
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


def test_interpolate_string_uses_dotenv_expansion() -> None:
    assert (
        interpolate_string(
            "${BLOODHOUND_HOST:-127.0.0.1}:${BLOODHOUND_PORT:-8080}:8080",
            {},
        )
        == "127.0.0.1:8080:8080"
    )


def test_compose_file_interpolates_ports_before_validation(tmp_path: Path) -> None:
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text(
        """
services:
  bloodhound:
    image: bloodhound
    ports:
      - "${BLOODHOUND_HOST:-127.0.0.1}:${BLOODHOUND_PORT:-8080}:8080"
"""
    )

    compose = ComposeConfig.from_file(compose_file)

    port = compose.services["bloodhound"].ports[0]
    assert port.to_container_arg() == "127.0.0.1:8080:8080"


def test_compose_file_interpolates_ports_from_env_file(tmp_path: Path) -> None:
    compose_file = tmp_path / "compose.yaml"
    env_file = tmp_path / ".env"
    compose_file.write_text(
        """
services:
  bloodhound:
    image: bloodhound
    ports:
      - "${BLOODHOUND_HOST:-127.0.0.1}:${BLOODHOUND_PORT:-8080}:8080"
"""
    )
    env_file.write_text("BLOODHOUND_HOST=0.0.0.0\nBLOODHOUND_PORT=9090\n")

    compose = ComposeConfig.from_file(compose_file, env_file=env_file)

    port = compose.services["bloodhound"].ports[0]
    assert port.to_container_arg() == "0.0.0.0:9090:8080"


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
