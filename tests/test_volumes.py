from pathlib import Path

from apple_compose.models import ComposeConfig
from apple_compose.volumes import volume_mount


def test_bind_mount_source_is_not_created(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate({"services": {"web": {"image": "nginx"}}})
    source = tmp_path / "missing"

    mount = volume_mount(
        f"{source}:/data",
        compose=compose,
        compose_dir=tmp_path,
        project_name="project",
    )

    assert mount == f"{source.resolve()}:/data"
    assert not source.exists()


def test_named_volume_source_uses_runtime_volume_name(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx"}},
            "volumes": {"data": {}},
        }
    )

    mount = volume_mount(
        "data:/data",
        compose=compose,
        compose_dir=tmp_path,
        project_name="project",
    )

    assert mount == "project-data:/data"


def test_named_volume_source_uses_explicit_name(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx"}},
            "volumes": {"data": {"name": "shared-data"}},
        }
    )

    mount = volume_mount(
        "data:/data",
        compose=compose,
        compose_dir=tmp_path,
        project_name="project",
    )

    assert mount == "shared-data:/data"


def test_external_named_volume_source_uses_compose_key(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx"}},
            "volumes": {"data": {"external": True}},
        }
    )

    mount = volume_mount(
        "data:/data",
        compose=compose,
        compose_dir=tmp_path,
        project_name="project",
    )

    assert mount == "data:/data"
