import pytest

from apple_compose.errors import ContainerRuntimeError
from apple_compose.models import ComposeConfig, NetworkConfig, NetworkList, NetworkSnapshot


def test_network_runtime_name_uses_explicit_name() -> None:
    assert NetworkConfig(name="shared").runtime_name("project", "default") == "shared"


def test_compose_creatable_network_names_skip_external() -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {"web": {"image": "nginx:alpine"}},
            "networks": {
                "default": {},
                "shared": {"external": True},
                "custom": {"name": "custom-name"},
            },
        }
    )

    assert compose.creatable_network_names("project") == ["project-default", "custom-name"]


def test_compose_service_network_names() -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {
                "web": {
                    "image": "nginx:alpine",
                    "networks": ["default", "custom"],
                }
            },
            "networks": {"custom": {"name": "custom-name"}},
        }
    )

    assert compose.service_network_names(compose.services["web"], "project") == [
        "project-default",
        "custom-name",
    ]


def test_network_list_extracts_runtime_ids() -> None:
    output = """
    [
      {"config":{"id":"default"},"id":"default","state":"running"},
      {"config":{"id":"fallback"},"state":"running"}
    ]
    """

    assert NetworkList.from_json(output).ids == {"default", "fallback"}


def test_network_snapshot_from_command_output() -> None:
    output = '[{"config":{"id":"bloodhoundce-default"},"id":"bloodhoundce-default"}]'

    assert NetworkSnapshot.from_command_output(output).existing == {
        "bloodhoundce-default"
    }


def test_network_list_rejects_invalid_json() -> None:
    with pytest.raises(ContainerRuntimeError, match="Invalid JSON from container network CLI"):
        NetworkList.from_json("not json")


def test_network_list_rejects_non_list_json() -> None:
    with pytest.raises(
        ContainerRuntimeError,
        match="Expected container network CLI JSON output to be a list",
    ):
        NetworkList.from_json("{}")
