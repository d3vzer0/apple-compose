import importlib
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import copy_sample, sample_text
from rich.console import Console
from typer.testing import CliRunner

from apple_compose.errors import ContainerRuntimeError, PlanningError
from apple_compose.main import app

runner = CliRunner()


class FakeContainerClient:
    def __init__(
        self,
        *,
        running: set[str] | None = None,
        existing: set[str] | None = None,
        running_by_service: dict[str, str] | None = None,
        existing_by_service: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        self.kwargs = kwargs
        self.running = (
            running
            if running is not None
            else {"apple-compose-db", "apple-compose-web"}
        )
        self.existing = existing if existing is not None else set(self.running)
        self.running_by_service = (
            running_by_service
            if running_by_service is not None
            else services_by_container_name(self.running)
        )
        self.existing_by_service = (
            existing_by_service
            if existing_by_service is not None
            else services_by_container_name(self.existing)
        )
        self.calls: list[tuple[str, Any]] = []

    def run(self, args: list[str], **kwargs: Any) -> Any:
        self.calls.append(("run", args))
        if not kwargs.get("capture_output"):
            return None
        if args == ["ls", "--format", "json"]:
            return SimpleNamespace(
                stdout=container_list_output(
                    self.running, by_service=self.running_by_service
                )
            )
        if args == ["ls", "--all", "--format", "json"]:
            return SimpleNamespace(
                stdout=container_list_output(
                    self.existing, by_service=self.existing_by_service
                )
            )
        return SimpleNamespace(stdout="[]")


def container_list_output(
    names: set[str], *, by_service: dict[str, str] | None = None
) -> str:
    by_service = by_service or {}
    by_service_items = frozenset(by_service.items())
    sample_by_service = {
        frozenset({("db", "apple-compose-db")}): "cli-labeled-apple-compose-db.json",
        frozenset({("web", "apple-compose-web")}): "cli-labeled-apple-compose-web.json",
        frozenset(
            {("db", "apple-compose-db"), ("web", "apple-compose-web")}
        ): "cli-labeled-apple-compose-web-db.json",
        frozenset({("web", "uuid-web")}): "cli-labeled-web.json",
        frozenset({("db", "uuid-db"), ("web", "uuid-web")}): "cli-labeled-web-db.json",
    }
    sample_by_name = {
        frozenset(): "empty.json",
        frozenset(
            {"apple-compose-db", "apple-compose-web"}
        ): "cli-default-running.json",
        frozenset({"apple-compose-db"}): "cli-db-running.json",
        frozenset({"apple-compose-web"}): "cli-web-running.json",
    }
    sample = sample_by_service.get(by_service_items, sample_by_name[frozenset(names)])
    return sample_text("container", sample)


def services_by_container_name(names: set[str]) -> dict[str, str]:
    services: dict[str, str] = {}
    for name in names:
        if name == "apple-compose-db":
            services["db"] = name
        elif name == "apple-compose-web":
            services["web"] = name
    return services


def command_calls(fake_client: FakeContainerClient) -> list[tuple[str, Any]]:
    return [call for call in fake_client.calls if call[1][0] != "ls"]


def test_help_registers_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "build",
        "config",
        "down",
        "exec",
        "images",
        "kill",
        "ls",
        "logs",
        "port",
        "ps",
        "pull",
        "restart",
        "rm",
        "run",
        "start",
        "stats",
        "stop",
        "up",
        "volumes",
        "version",
    ):
        assert command in result.output


def test_ls_groups_apple_compose_projects(monkeypatch, tmp_path: Path) -> None:
    ls_main = importlib.import_module("apple_compose.commands.ls.main")

    fake_client = FakeContainerClient(
        running=set(),
        existing=set(),
        existing_by_service={"web": "uuid-web", "db": "uuid-db"},
    )
    monkeypatch.setattr(ls_main, "ContainerClient", lambda **kwargs: fake_client)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["ls"])

    assert result.exit_code == 0
    assert "apple-compose" in result.output
    assert "2" in result.output
    assert command_calls(fake_client) == []
    assert fake_client.calls == [("run", ["ls", "--all", "--format", "json"])]


def test_version_does_not_require_compose_file(monkeypatch, tmp_path: Path) -> None:
    version_main = importlib.import_module("apple_compose.commands.version.main")

    monkeypatch.setattr(version_main, "package_version", lambda package: "1.2.3")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "apple-compose 1.2.3" in result.output


def test_up_dry_run_uses_default_file(tmp_path: Path, monkeypatch) -> None:
    copy_sample(
        tmp_path,
        "compose",
        "basic-web-nginx-alpine.yaml",
        name="docker-compose.yml",
    )
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["--dry-run", "up", "-d"])

    assert result.exit_code == 0
    assert "container rm --force" not in result.output
    assert "container run -d --name" in result.output


def test_up_dry_run_includes_resource_limits(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "resource-limits.yaml")

    result = runner.invoke(app, ["--dry-run", "-f", str(compose_file), "up", "-d"])

    assert result.exit_code == 0
    assert "--cpus 2" in result.output
    assert "--memory 512M" in result.output


def test_ps_uses_global_file_option(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "basic-web-nginx-alpine.yaml")

    result = runner.invoke(app, ["--file", str(compose_file), "ps"])

    assert result.exit_code == 0
    assert "web" in result.output
    assert "nginx:alpine" in result.output


def test_images_shows_planned_service_images(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "images", "web"])

    assert result.exit_code == 0
    assert "db" in result.output
    assert "postgres:16" in result.output
    assert "web" in result.output
    assert "nginx:alpine" in result.output


def test_port_shows_configured_ports(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "web-with-port.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "port", "web"])

    assert result.exit_code == 0
    assert "web" in result.output
    assert "0.0.0.0:8080:80" in result.output


def test_port_requires_configured_ports(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "basic-web-nginx-alpine.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "port", "web"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "Service has no published ports: web"


def test_config_shows_supported_compose_config(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "config-summary.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "config"])

    assert result.exit_code == 0
    assert "Project: apple-compose" in result.output
    assert "web" in result.output
    assert "nginx:alpine" in result.output
    assert "appnet" in result.output
    assert "data" in result.output


def test_pull_pulls_image_backed_services(tmp_path: Path, monkeypatch) -> None:
    pull_main = importlib.import_module("apple_compose.commands.pull.main")

    fake_client = FakeContainerClient(running=set(), existing=set())
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(pull_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "pull", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["image", "pull", "postgres:16"]),
        ("run", ["image", "pull", "nginx:alpine"]),
    ]


def test_pull_skips_build_only_services(tmp_path: Path, monkeypatch) -> None:
    pull_main = importlib.import_module("apple_compose.commands.pull.main")

    fake_client = FakeContainerClient(running=set(), existing=set())
    compose_file = copy_sample(tmp_path, "compose", "build-only-web.yaml")
    monkeypatch.setattr(pull_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "pull"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == []
    assert "No pullable services selected." in result.output


def test_up_runs_service_without_removing_container(
    tmp_path: Path, monkeypatch
) -> None:
    from apple_compose.commands.up import main as up_main

    fake_client = FakeContainerClient(running=set(), existing=set())
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(up_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "up", "-d"])

    assert result.exit_code == 0
    assert ("run", ["rm", "--force", "apple-compose-web"]) not in command_calls(
        fake_client
    )
    assert (
        "run",
        [
            "run",
            "-d",
            "--name",
            "apple-compose-web",
            "--label",
            "com.apple.compose.created-by=apple-compose",
            "--label",
            "com.docker.compose.project=apple-compose",
            "--label",
            "com.docker.compose.service=web",
            "--",
            "nginx:alpine",
        ],
    ) in command_calls(fake_client)


def test_up_skips_running_services(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.up import main as up_main

    fake_client = FakeContainerClient(
        running_by_service={"web": "apple-compose-web"},
        existing_by_service={"web": "apple-compose-web"},
    )
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(up_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "up", "-d"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == []


def test_up_starts_existing_stopped_services(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.up import main as up_main

    fake_client = FakeContainerClient(
        running=set(),
        existing_by_service={"web": "apple-compose-web"},
    )
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(up_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "up", "-d"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["start", "apple-compose-web"])]


def test_up_runs_missing_services_after_skipping_running_dependencies(
    tmp_path: Path, monkeypatch
) -> None:
    from apple_compose.commands.up import main as up_main

    fake_client = FakeContainerClient(
        running_by_service={"db": "apple-compose-db"},
        existing_by_service={"db": "apple-compose-db"},
    )
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(up_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "up", "-d", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        (
            "run",
            [
                "run",
                "-d",
                "--name",
                "apple-compose-web",
                "--label",
                "com.apple.compose.created-by=apple-compose",
                "--label",
                "com.docker.compose.project=apple-compose",
                "--label",
                "com.docker.compose.service=web",
                "--",
                "nginx:alpine",
            ],
        )
    ]


def test_up_fails_when_planned_container_name_is_unmanaged(
    tmp_path: Path, monkeypatch
) -> None:
    from apple_compose.commands.up import main as up_main

    fake_client = FakeContainerClient(
        running=set(),
        existing={"apple-compose-web"},
        existing_by_service={},
    )
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(up_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "up", "-d"])

    assert result.exit_code != 0
    assert (
        str(result.exception)
        == "Container already exists but is not managed by apple-compose: apple-compose-web"
    )
    assert command_calls(fake_client) == []


def test_down_removes_containers_with_force(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.down import main as down_main

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(down_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "down"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["rm", "--force", "apple-compose-web"])
    ]


def test_stop_stops_services_in_reverse_dependency_order(
    tmp_path: Path, monkeypatch
) -> None:
    from apple_compose.commands.stop import main as stop_main

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(stop_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(
        app, ["-f", str(compose_file), "stop", "--signal", "SIGTERM", "--time", "5"]
    )

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        (
            "run",
            [
                "stop",
                "--signal",
                "SIGTERM",
                "--time",
                "5",
                "apple-compose-web",
                "apple-compose-db",
            ],
        )
    ]


def test_stop_skips_missing_containers(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.stop import main as stop_main

    fake_client = FakeContainerClient(running={"apple-compose-db"})
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(stop_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "stop"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["stop", "apple-compose-db"])]


def test_stop_prefers_labeled_container_id(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.stop import main as stop_main

    fake_client = FakeContainerClient(
        running=set(),
        existing=set(),
        running_by_service={"web": "uuid-web"},
        existing_by_service={"web": "uuid-web"},
    )
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(stop_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "stop", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["stop", "uuid-web"])]


def test_start_starts_existing_services_in_dependency_order(
    tmp_path: Path, monkeypatch
) -> None:
    start_main = importlib.import_module("apple_compose.commands.start.main")

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(start_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "start", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["start", "apple-compose-db"]),
        ("run", ["start", "apple-compose-web"]),
    ]


def test_start_prefers_labeled_container_ids(tmp_path: Path, monkeypatch) -> None:
    start_main = importlib.import_module("apple_compose.commands.start.main")

    fake_client = FakeContainerClient(
        running=set(),
        existing=set(),
        existing_by_service={"web": "uuid-web"},
    )
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(start_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "start", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["start", "uuid-web"])]


def test_exec_runs_command_in_running_service(tmp_path: Path, monkeypatch) -> None:
    exec_main = importlib.import_module("apple_compose.commands.exec.main")

    fake_client = FakeContainerClient(running_by_service={"web": "uuid-web"})
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(exec_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(
        app,
        ["-f", str(compose_file), "exec", "--tty", "web", "--", "sh", "-lc", "echo ok"],
    )

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["exec", "--tty", "uuid-web", "sh", "-lc", "echo ok"])
    ]


def test_exec_requires_command(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "exec", "web"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "exec requires a command"


def test_exec_requires_separator_before_command(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "exec", "web", "sh"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "exec command must follow --"


def test_exec_requires_running_service(tmp_path: Path, monkeypatch) -> None:
    exec_main = importlib.import_module("apple_compose.commands.exec.main")

    fake_client = FakeContainerClient(running=set(), existing={"apple-compose-web"})
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(exec_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "exec", "web", "--", "sh"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "Service is not running: web"


def test_exec_targets_requested_service_not_dependency(
    tmp_path: Path, monkeypatch
) -> None:
    exec_main = importlib.import_module("apple_compose.commands.exec.main")

    fake_client = FakeContainerClient(
        running_by_service={"web": "uuid-web", "db": "uuid-db"}
    )
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(exec_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "exec", "web", "--", "sh"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["exec", "uuid-web", "sh"])]


def test_exec_passes_option_like_command_args_after_service(
    tmp_path: Path, monkeypatch
) -> None:
    exec_main = importlib.import_module("apple_compose.commands.exec.main")

    fake_client = FakeContainerClient(running_by_service={"web": "uuid-web"})
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(exec_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(
        app, ["-f", str(compose_file), "exec", "web", "--", "--user", "root"]
    )

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["exec", "uuid-web", "--user", "root"])
    ]


def test_run_executes_one_off_service_without_name(tmp_path: Path, monkeypatch) -> None:
    run_main = importlib.import_module("apple_compose.commands.run.main")

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(run_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(
        app, ["-f", str(compose_file), "run", "--rm", "web", "--", "echo", "ok"]
    )

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        (
            "run",
            [
                "run",
                "--label",
                "com.apple.compose.created-by=apple-compose",
                "--label",
                "com.docker.compose.project=apple-compose",
                "--label",
                "com.docker.compose.service=web",
                "--label",
                "com.docker.compose.oneoff=True",
                "--rm",
                "--",
                "nginx:alpine",
                "echo",
                "ok",
            ],
        )
    ]


def test_run_targets_requested_service_not_dependency(
    tmp_path: Path, monkeypatch
) -> None:
    run_main = importlib.import_module("apple_compose.commands.run.main")

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(run_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "run", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client)[0][1][-1] == "nginx:alpine"


def test_run_requires_separator_before_command(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "run", "web", "echo"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "run command must follow --"


def test_run_passes_option_like_command_args_after_service(
    tmp_path: Path, monkeypatch
) -> None:
    run_main = importlib.import_module("apple_compose.commands.run.main")

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(run_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "run", "web", "--", "--help"])

    assert result.exit_code == 0
    assert command_calls(fake_client)[0][1][-1] == "--help"


def test_rm_removes_existing_services_in_reverse_dependency_order(
    tmp_path: Path, monkeypatch
) -> None:
    rm_main = importlib.import_module("apple_compose.commands.rm.main")

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(rm_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "rm", "--force", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["rm", "--force", "apple-compose-web", "apple-compose-db"])
    ]


def test_rm_prefers_labeled_container_ids(tmp_path: Path, monkeypatch) -> None:
    rm_main = importlib.import_module("apple_compose.commands.rm.main")

    fake_client = FakeContainerClient(
        running=set(),
        existing=set(),
        existing_by_service={"web": "uuid-web"},
    )
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(rm_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "rm", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["rm", "uuid-web"])]


def test_kill_kills_running_services_in_reverse_dependency_order(
    tmp_path: Path, monkeypatch
) -> None:
    kill_main = importlib.import_module("apple_compose.commands.kill.main")

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(kill_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(
        app, ["-f", str(compose_file), "kill", "--signal", "KILL", "web"]
    )

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["kill", "--signal", "KILL", "apple-compose-web", "apple-compose-db"])
    ]


def test_kill_skips_stopped_services(tmp_path: Path, monkeypatch) -> None:
    kill_main = importlib.import_module("apple_compose.commands.kill.main")

    fake_client = FakeContainerClient(running={"apple-compose-db"})
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(kill_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "kill"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["kill", "apple-compose-db"])]


def test_restart_stops_then_starts_services(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.restart import main as restart_main

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(restart_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "restart", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["stop", "apple-compose-web", "apple-compose-db"]),
        ("run", ["start", "apple-compose-db"]),
        ("run", ["start", "apple-compose-web"]),
    ]


def test_restart_starts_existing_stopped_service_without_stopping_it(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from apple_compose.commands.restart import main as restart_main

    fake_client = FakeContainerClient(running=set(), existing={"apple-compose-web"})
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(restart_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "restart", "web"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["start", "apple-compose-web"])]


def test_logs_passes_native_options(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.logs import main as logs_main

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(logs_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(
        app, ["-f", str(compose_file), "logs", "--boot", "-n", "10", "web"]
    )

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["logs", "--boot", "-n", "10", "apple-compose-web"])
    ]


def test_logs_follow_requires_one_service(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "logs", "--follow"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "logs --follow requires exactly one service"


def test_logs_follow_requires_running_service(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.logs import main as logs_main

    fake_client = FakeContainerClient(running=set(), existing={"apple-compose-web"})
    compose_file = copy_sample(tmp_path, "compose", "named-web-nginx-alpine.yaml")
    monkeypatch.setattr(logs_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "logs", "--follow", "web"])

    assert result.exit_code == 1
    assert isinstance(result.exception, PlanningError)
    assert str(result.exception) == "Service is not running: web"


def test_stats_targets_project_services(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.stats import main as stats_main

    fake_client = FakeContainerClient()
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(stats_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "stats", "--no-stream"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [
        ("run", ["stats", "apple-compose-db", "apple-compose-web", "--no-stream"])
    ]


def test_stats_skips_stopped_services(tmp_path: Path, monkeypatch) -> None:
    from apple_compose.commands.stats import main as stats_main

    fake_client = FakeContainerClient(running={"apple-compose-db"})
    compose_file = copy_sample(tmp_path, "compose", "web-db-depends.yaml")
    monkeypatch.setattr(stats_main, "ContainerClient", lambda **kwargs: fake_client)

    result = runner.invoke(app, ["-f", str(compose_file), "stats"])

    assert result.exit_code == 0
    assert command_calls(fake_client) == [("run", ["stats", "apple-compose-db"])]


def test_volumes_shows_declared_compose_volumes(tmp_path: Path) -> None:
    compose_file = copy_sample(tmp_path, "compose", "volumes-summary.yaml")

    result = runner.invoke(app, ["-f", str(compose_file), "volumes"])

    assert result.exit_code == 0
    assert "data" in result.output
    assert "apple-compose-data" in result.output
    assert "shared" in result.output


def test_main_prints_user_facing_error_without_traceback(monkeypatch) -> None:
    from apple_compose import main

    def fail() -> None:
        raise ContainerRuntimeError("runtime failed")

    output = StringIO()
    monkeypatch.setattr(main, "app", fail)
    monkeypatch.setattr(
        main,
        "console",
        Console(file=output, force_terminal=False, color_system=None),
    )

    with pytest.raises(SystemExit) as exc_info:
        main.main()

    assert exc_info.value.code == 1
    assert output.getvalue() == "runtime failed\n"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__
