from pathlib import Path

import pytest
from pydantic import ValidationError

from apple_compose.models import ComposeConfig
from apple_compose.planner import Planner


def test_bind_mount_source_is_not_created(tmp_path: Path) -> None:
    source = tmp_path / "missing"
    compose = ComposeConfig.model_validate(
        {"services": {"web": {"image": "nginx", "volumes": [f"{source}:/data"]}}}
    )

    plan = Planner(compose=compose, compose_path=tmp_path / "compose.yaml", cwd=tmp_path).create_plan()

    assert plan.services[0].mounts == [f"{source.resolve()}:/data"]
    assert not source.exists()


def test_named_volume_source_uses_runtime_volume_name(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx", "volumes": ["data:/data"]}},
            "volumes": {"data": {}},
        }
    )

    plan = Planner(
        compose=compose,
        compose_path=tmp_path / "compose.yaml",
        cwd=tmp_path,
        project_name="project",
    ).create_plan()

    assert plan.services[0].mounts == ["project-data:/data"]


def test_named_volume_source_uses_explicit_name(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx", "volumes": ["data:/data"]}},
            "volumes": {"data": {"name": "shared-data"}},
        }
    )

    plan = Planner(
        compose=compose,
        compose_path=tmp_path / "compose.yaml",
        cwd=tmp_path,
        project_name="project",
    ).create_plan()

    assert plan.services[0].mounts == ["shared-data:/data"]


def test_external_named_volume_source_uses_compose_key(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx", "volumes": ["data:/data"]}},
            "volumes": {"data": {"external": True}},
        }
    )

    plan = Planner(
        compose=compose,
        compose_path=tmp_path / "compose.yaml",
        cwd=tmp_path,
        project_name="project",
    ).create_plan()

    assert plan.services[0].mounts == ["data:/data"]


def test_empty_volume_source_is_rejected_by_service_model() -> None:
    with pytest.raises(ValidationError, match="Volume source must not be empty"):
        ComposeConfig.model_validate(
            {
                "services": {
                    "web": {
                        "image": "nginx",
                        "volumes": [":/data"],
                    }
                }
            }
        )
