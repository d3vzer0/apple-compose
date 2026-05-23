from pathlib import Path

import pytest

from apple_compose.errors import PlanningError
from apple_compose.models import ComposeConfig
from apple_compose.planner import Planner, create_plan, resolve_project_name
from conftest import copy_sample


def test_plan_orders_dependencies_and_generates_run_args(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "planner-web-db-env-port.yaml")
    compose = ComposeConfig.from_file(compose_file)

    plan = Planner(
        compose=compose,
        compose_path=compose_file,
        cwd=tmp_path,
        project_name=None,
        requested_services=["web"],
        detach=True,
    ).create_plan()

    assert plan.project_name == "my_app"
    assert [service.service_name for service in plan.services] == ["db", "web"]
    web = plan.services[1]
    assert web.service is compose.services["web"]
    assert web.container_name == "my_app-web"
    assert web.environment == {"FOO": "${FOO:-bar}"}
    assert web.run_args == [
        "-d",
        "--name",
        "my_app-web",
        "--label",
        "com.apple.compose.created-by=apple-compose",
        "--label",
        "com.docker.compose.project=my_app",
        "--label",
        "com.docker.compose.service=web",
        "--env",
        "FOO=${FOO:-bar}",
        "-p",
        "0.0.0.0:8080:80",
        "--",
        "nginx:alpine",
    ]


def test_create_plan_wrapper_uses_planner(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "basic-web-nginx.yaml")
    compose = ComposeConfig.from_file(compose_file)

    plan = create_plan(
        compose,
        compose_path=compose_file,
        cwd=tmp_path,
        project_name=None,
    )

    assert [service.service_name for service in plan.services] == ["web"]


def test_service_plan_renders_image_and_command_last(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "service-command-host-port.yaml")
    compose = ComposeConfig.from_file(compose_file)

    plan = Planner(
        compose=compose,
        compose_path=compose_file,
        cwd=tmp_path,
        project_name=None,
    ).create_plan()

    args = plan.services[0].run_args
    image_separator_index = args.index("--")

    assert args[image_separator_index:] == ["--", "nginx", "nginx", "-g", "daemon off;"]
    assert "--hostname" in args[:image_separator_index]
    assert "-p" in args[:image_separator_index]


def test_service_plan_renders_resource_limits(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "resource-limits.yaml")
    compose = ComposeConfig.from_file(compose_file)

    plan = Planner(
        compose=compose,
        compose_path=compose_file,
        cwd=tmp_path,
        project_name=None,
    ).create_plan()

    args = plan.services[0].run_args
    cpus_index = args.index("--cpus")
    memory_index = args.index("--memory")

    assert args[cpus_index : cpus_index + 2] == ["--cpus", "2"]
    assert args[memory_index : memory_index + 2] == ["--memory", "512M"]
    assert cpus_index < args.index("--")
    assert memory_index < args.index("--")


def test_service_plan_discovers_container_arg_renderers_in_definition_order(
    tmp_path: Path,
) -> None:
    compose_file = copy_sample(tmp_path, "compose", "basic-web-nginx.yaml")
    compose = ComposeConfig.from_file(compose_file)

    plan = Planner(
        compose=compose,
        compose_path=compose_file,
        cwd=tmp_path,
        project_name=None,
    ).create_plan()

    renderer_names = [renderer.__name__ for renderer in plan.services[0]._container_arg_renderers()]

    assert renderer_names[:4] == ["_detach_args", "_name_args", "_label_args", "_environment_args"]
    assert "_entrypoint_args" in renderer_names
    assert "_image_and_command_args" not in renderer_names


def test_unknown_requested_service_fails_during_planning(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "basic-web-nginx.yaml")
    compose = ComposeConfig.from_file(compose_file)

    with pytest.raises(PlanningError):
        Planner(
            compose=compose,
            compose_path=compose_file,
            cwd=tmp_path,
            project_name=None,
            requested_services=["missing"],
        ).create_plan()


def test_resolve_project_name_replaces_leading_dot(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "hidden-project-name.yaml")
    compose = ComposeConfig.from_file(compose_file)

    assert resolve_project_name(compose, tmp_path) == "_hidden"
