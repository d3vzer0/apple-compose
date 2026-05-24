from apple_compose.models import ComposeConfig, NetworkConfig


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
