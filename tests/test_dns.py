import json
from pathlib import Path
from types import SimpleNamespace

from apple_compose.dns import (
    CoreDnsConfig,
    HostsRecord,
    InspectedContainer,
    NetworkAddress,
    create_dns_service,
    ensure_dns_sidecar,
    inspect_container,
    render_corefile,
    render_hosts_file,
    write_coredns_config,
)
from apple_compose.models import ComposeConfig
from apple_compose.planner import Planner


class FakeInspectClient:
    def run(self, args: list[str], **kwargs):
        assert args == ["inspect", "web"]
        assert kwargs == {"capture_output": True}
        return SimpleNamespace(
            stdout=json.dumps(
                [
                    {
                        "configuration": {"id": "web"},
                        "networks": [
                            {
                                "network": "project-default",
                                "address": "10.89.0.4/24",
                                "gateway": "10.89.0.1",
                            }
                        ],
                    }
                ]
            )
        )


class AppleInspectClient:
    def run(self, args: list[str], **kwargs):
        assert args == ["inspect", "bloodhoundce-app-db"]
        assert kwargs == {"capture_output": True}
        return SimpleNamespace(
            stdout=json.dumps(
                [
                    {
                        "configuration": {
                            "id": "bloodhoundce-app-db",
                            "image": {"reference": "docker.io/library/postgres:16"},
                        },
                        "networks": [
                            {
                                "hostname": "bloodhoundce-app-db",
                                "ipv4Gateway": "192.168.64.1",
                                "ipv4Address": "192.168.64.18/24",
                                "network": "default",
                                "ipv6Address": "fdd6:a939:e850:b03e::1/64",
                            }
                        ],
                    }
                ]
            )
        )


class ExistingDnsSidecarClient:
    dry_run = False

    def __init__(self, image: str) -> None:
        self.image = image
        self.calls: list[list[str]] = []

    def run(self, args: list[str], **kwargs):
        self.calls.append(args)
        if kwargs.get("capture_output"):
            return SimpleNamespace(
                stdout=json.dumps(
                    [
                        {
                            "configuration": {
                                "id": "project-dns",
                                "image": {"reference": self.image},
                            },
                            "networks": [],
                        }
                    ]
                )
            )
        return None


def test_inspect_container_extracts_network_addresses() -> None:
    inspected = inspect_container(FakeInspectClient(), "web")  # type: ignore[arg-type]

    assert inspected.name == "web"
    assert inspected.networks["project-default"].ipv4 == ["10.89.0.4"]


def test_inspect_container_extracts_apple_network_shape() -> None:
    inspected = inspect_container(AppleInspectClient(), "bloodhoundce-app-db")  # type: ignore[arg-type]

    assert inspected.name == "bloodhoundce-app-db"
    assert inspected.image == "docker.io/library/postgres:16"
    assert inspected.networks["default"].ipv4 == ["192.168.64.18"]


def test_ensure_dns_sidecar_recreates_stale_image(tmp_path: Path) -> None:
    client = ExistingDnsSidecarClient("apple-compose-dns:local")
    config_dir = tmp_path / "dns"
    dns_service = create_dns_service(_basic_plan(tmp_path), config_dir)

    ensure_dns_sidecar(
        client,  # type: ignore[arg-type]
        dns_service,
        config_dir,
        running=set(),
        existing={"project-dns"},
    )

    assert client.calls[0] == ["inspect", "project-dns"]
    assert client.calls[1] == ["rm", "--force", "project-dns"]
    assert client.calls[2] == [
        "run",
        "-d",
        "--name",
        "project-dns",
        "--label",
        "com.apple.compose.created-by=apple-compose",
        "--label",
        "com.apple.compose.role=dns",
        "--label",
        "com.docker.compose.project=project",
        "-v",
        f"{config_dir}:/config",
        "--network",
        "project-default",
        "--",
        "coredns/coredns:1.12.1",
        "-conf",
        "/config/Corefile",
    ]


def test_ensure_dns_sidecar_starts_matching_existing_image(tmp_path: Path) -> None:
    client = ExistingDnsSidecarClient("docker.io/coredns/coredns:1.12.1")
    config_dir = tmp_path / "dns"
    dns_service = create_dns_service(_basic_plan(tmp_path), config_dir)

    ensure_dns_sidecar(
        client,  # type: ignore[arg-type]
        dns_service,
        config_dir,
        running=set(),
        existing={"project-dns"},
    )

    assert client.calls == [
        ["inspect", "project-dns"],
        ["start", "project-dns"],
    ]


def test_render_corefile_uses_hosts_auto_reload() -> None:
    rendered = render_corefile()

    assert "hosts /config/hosts" in rendered
    assert "ttl" not in rendered
    assert "reload 1s" in rendered
    assert "forward . /etc/resolv.conf" in rendered


def test_render_hosts_file_uses_hosts_syntax() -> None:
    rendered = render_hosts_file(
        CoreDnsConfig(
            records=[
                HostsRecord(
                    ip="10.89.0.3",
                    aliases=["db", "project-db"],
                )
            ],
        )
    )

    assert rendered == "10.89.0.3 db project-db\n"


def test_render_hosts_file_supports_no_records() -> None:
    rendered = render_hosts_file(CoreDnsConfig(records=[]))

    assert rendered == ""


def test_coredns_hosts_file_uses_service_and_container_aliases(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {
            "services": {
                "db": {
                    "image": "postgres:16",
                    "container_name": "database",
                    "networks": {"backend": {"aliases": ["postgres"]}},
                }
            },
            "networks": {"backend": {}},
        }
    )
    plan = Planner(
        compose=compose,
        compose_path=tmp_path / "compose.yaml",
        cwd=tmp_path,
        project_name="project",
    ).create_plan()
    config_dir = tmp_path / "dns"

    write_coredns_config(
        config_dir,
        services=plan.services,
        inspected_services={
            "database": InspectedContainer(
                name="database",
                networks={
                    "project-backend": NetworkAddress(
                        network_name="project-backend",
                        ipv4=["10.89.0.3"],
                        ipv6=["fdf4::3"],
                    )
                },
            )
        },
    )

    assert (tmp_path / "dns" / "Corefile").exists()
    assert (tmp_path / "dns" / "hosts").read_text() == (
        "10.89.0.3 db database postgres\n"
    )


def test_coredns_hosts_file_matches_inspect_network_key(tmp_path: Path) -> None:
    compose = ComposeConfig.model_validate(
        {"services": {"app-db": {"image": "postgres:16"}}}
    )
    plan = Planner(
        compose=compose,
        compose_path=tmp_path / "compose.yaml",
        cwd=tmp_path,
        project_name="bloodhoundce",
    ).create_plan()
    config_dir = tmp_path / "dns"

    write_coredns_config(
        config_dir,
        services=plan.services,
        inspected_services={
            "bloodhoundce-app-db": InspectedContainer(
                name="bloodhoundce-app-db",
                networks={
                    "default": NetworkAddress(
                        network_name="default",
                        ipv4=["192.168.64.18"],
                    )
                },
            )
        },
    )

    assert (tmp_path / "dns" / "hosts").read_text() == (
        "192.168.64.18 app-db bloodhoundce-app-db\n"
    )


def _basic_plan(tmp_path: Path):
    compose = ComposeConfig.model_validate({"services": {"web": {"image": "nginx"}}})
    return Planner(
        compose=compose,
        compose_path=tmp_path / "compose.yaml",
        cwd=tmp_path,
        project_name="project",
    ).create_plan()
