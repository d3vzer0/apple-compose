from types import SimpleNamespace

import pytest

from apple_compose.errors import ContainerRuntimeError
from apple_compose.models import ContainerList, ContainerSnapshot
from conftest import sample_text


def test_container_list_extracts_configuration_ids() -> None:
    containers = ContainerList.from_json(sample_text("container", "extract-configuration-ids.json"))

    assert containers.ids == {"web", "db"}


def test_container_list_empty_output_is_empty() -> None:
    assert ContainerList.from_command_output("").ids == set()


def test_container_list_maps_apple_compose_labels_by_service() -> None:
    containers = ContainerList.from_json(sample_text("container", "labeled-services.json"))

    assert containers.ids_by_service(project_name="project") == {"web": "uuid-web"}


def test_container_list_groups_apple_compose_projects() -> None:
    containers = ContainerList.from_json(sample_text("container", "project-summaries.json"))

    assert containers.project_summaries()[0].project == "project"
    assert containers.project_summaries()[0].containers == 2
    assert containers.project_summaries()[0].running == 1


def test_container_snapshot_from_command_outputs_builds_label_maps() -> None:
    snapshot = ContainerSnapshot.from_command_outputs(
        running_output=sample_text("container", "snapshot-running.json"),
        existing_output=sample_text("container", "snapshot-existing.json"),
        project_name="project",
    )

    assert snapshot.running == {"uuid-web"}
    assert snapshot.existing == {"uuid-web", "project-db"}
    assert snapshot.running_by_service == {"web": "uuid-web"}
    assert snapshot.existing_by_service == {"web": "uuid-web"}


def test_container_snapshot_prefers_labels_and_falls_back_to_names() -> None:
    snapshot = ContainerSnapshot(
        running={"project-db"},
        existing={"project-db", "uuid-web"},
        running_by_service={"web": "uuid-web"},
        existing_by_service={"web": "uuid-web"},
    )
    services = [
        SimpleNamespace(service_name="db", container_name="project-db"),
        SimpleNamespace(service_name="web", container_name="project-web"),
    ]

    assert snapshot.running_for_services(services) == ["project-db", "uuid-web"]
    assert snapshot.existing_for_services(services) == ["project-db", "uuid-web"]


def test_container_list_rejects_invalid_json() -> None:
    with pytest.raises(ContainerRuntimeError, match="Invalid JSON from container CLI"):
        ContainerList.from_json(sample_text("container", "invalid-json.txt"))


def test_container_list_rejects_non_list_json() -> None:
    with pytest.raises(ContainerRuntimeError, match="Expected container CLI JSON output to be a list"):
        ContainerList.from_json(sample_text("container", "non-list.json"))
