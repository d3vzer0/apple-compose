from types import SimpleNamespace
from typing import Any

from apple_compose.models import ContainerSnapshot
from apple_compose.runtime import load_container_snapshot, load_network_snapshot
from conftest import sample_text


class FakeContainerClient:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, Any]]] = []

    def run(self, args: list[str], **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        if args == ["ls", "--format", "json"]:
            return SimpleNamespace(stdout=sample_text("container", "runtime-running.json"))
        if args == ["ls", "--all", "--format", "json"]:
            return SimpleNamespace(stdout=sample_text("container", "runtime-existing.json"))
        if args == ["network", "ls", "--format=json"]:
            return SimpleNamespace(stdout='[{"id":"project-default"}]')
        return SimpleNamespace(stdout="[]")


def test_load_container_snapshot_reads_running_and_existing_containers() -> None:
    client = FakeContainerClient()

    snapshot = load_container_snapshot(client, project_name="project")  # type: ignore[arg-type]

    assert snapshot.running == {"web"}
    assert snapshot.existing == {"web", "db"}
    assert client.calls == [
        (["ls", "--format", "json"], {"capture_output": True}),
        (["ls", "--all", "--format", "json"], {"capture_output": True}),
    ]


def test_container_snapshot_filters_names_in_input_order() -> None:
    snapshot = ContainerSnapshot(
        running={"db"},
        existing={"db", "web"},
        running_by_service={},
        existing_by_service={},
    )

    assert snapshot.filter_running(["web", "db"]) == ["db"]
    assert snapshot.filter_existing(["web", "missing", "db"]) == ["web", "db"]


def test_load_network_snapshot_reads_existing_networks() -> None:
    client = FakeContainerClient()

    snapshot = load_network_snapshot(client)  # type: ignore[arg-type]

    assert snapshot.existing == {"project-default"}
    assert client.calls == [
        (["network", "ls", "--format=json"], {"capture_output": True}),
    ]
