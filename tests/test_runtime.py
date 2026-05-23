from types import SimpleNamespace
from typing import Any

from apple_compose.models import ContainerSnapshot
from apple_compose.runtime import load_container_snapshot
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
