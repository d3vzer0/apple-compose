from pathlib import Path

import pytest

from apple_compose.errors import ComposeValidationError
from apple_compose.models import ComposeConfig
from conftest import copy_sample


def test_compose_config_from_file(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "basic-web-nginx-alpine.yaml")

    config = ComposeConfig.from_file(compose_file)

    assert config.services["web"].image == "nginx:alpine"
    assert config.warnings == []


def test_compose_config_from_file_rejects_duplicate_keys(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "duplicate-image.yaml")

    with pytest.raises(ComposeValidationError):
        ComposeConfig.from_file(compose_file)


def test_compose_config_from_file_rejects_unknown_dependency(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "unknown-dependency.yaml")

    with pytest.raises(ComposeValidationError):
        ComposeConfig.from_file(compose_file)


def test_compose_config_from_file_rejects_dependency_cycle(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "dependency-cycle.yaml")

    with pytest.raises(ComposeValidationError):
        ComposeConfig.from_file(compose_file)


def test_compose_config_from_file_rejects_long_volume_syntax(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "long-volume-syntax.yaml")

    with pytest.raises(ComposeValidationError):
        ComposeConfig.from_file(compose_file)


def test_compose_config_warns_for_ignored_shm_size(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "resource-limits.yaml")

    config = ComposeConfig.from_file(compose_file)

    assert config.services["web"].shm_size == "1gb"
    assert "Parsed but not implemented for service web: shm_size" in config.warnings


def test_compose_config_warns_for_unsupported_hostname() -> None:
    config = ComposeConfig.model_validate(
        {"services": {"web": {"image": "nginx:alpine", "hostname": "web"}}}
    )

    assert "Ignoring unsupported key on service web: hostname" in config.warnings
