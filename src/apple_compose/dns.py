import hashlib
import ipaddress
import json
import os
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from apple_compose.container_cli import ContainerClient
from apple_compose.errors import ContainerRuntimeError
from apple_compose.labels import (
    APPLE_COMPOSE_CREATED_BY_LABEL,
    APPLE_COMPOSE_CREATED_BY_VALUE,
    APPLE_COMPOSE_DNS_ROLE,
    APPLE_COMPOSE_ROLE_LABEL,
    DOCKER_COMPOSE_PROJECT_LABEL,
)
from apple_compose.models import ServiceConfig
from apple_compose.planner import AppPlan, NetworkAttachment, ServicePlan

DNS_IMAGE_ENV = "APPLE_COMPOSE_DNS_IMAGE"
DEFAULT_DNS_IMAGE = "coredns/coredns:1.12.1"


@dataclass
class NetworkAddress:
    network_name: str
    ipv4: list[str] = field(default_factory=list)
    ipv6: list[str] = field(default_factory=list)


@dataclass
class InspectedContainer:
    name: str
    networks: dict[str, NetworkAddress]
    image: str | None = None

    def ip_for_network(self, network_name: str) -> str | None:
        network = self.networks.get(network_name)
        if not network:
            return None
        return (network.ipv4 or [None])[0]


@dataclass
class HostsRecord:
    ip: str
    aliases: list[str]


@dataclass
class CoreDnsConfig:
    records: list[HostsRecord]


def create_dns_service(plan: AppPlan, config_dir: Path) -> ServicePlan:
    image = os.environ.get(DNS_IMAGE_ENV, DEFAULT_DNS_IMAGE)
    return ServicePlan(
        service_name="dns",
        service=ServiceConfig(image=image, command=["-conf", "/config/Corefile"]),
        container_name=f"{plan.project_name}-dns",
        image=image,
        labels=_sidecar_labels(plan.project_name),
        env_files=[],
        environment={},
        mounts=[f"{config_dir}:/config"],
        network_attachments=_dns_network_attachments(plan),
        detach=True,
    )


def dns_config_dir(compose_path: Path, project_name: str) -> Path:
    key = hashlib.sha256(
        f"{compose_path.resolve()}\0{project_name}".encode("utf-8")
    ).hexdigest()[:16]
    return Path.home() / ".local" / "share" / "apple-compose" / "projects" / key / "dns"


def _sidecar_labels(project_name: str) -> dict[str, str]:
    return {
        APPLE_COMPOSE_CREATED_BY_LABEL: APPLE_COMPOSE_CREATED_BY_VALUE,
        APPLE_COMPOSE_ROLE_LABEL: APPLE_COMPOSE_DNS_ROLE,
        DOCKER_COMPOSE_PROJECT_LABEL: project_name,
    }


def ensure_dns_sidecar(
    client: ContainerClient,
    dns_service: ServicePlan,
    config_dir: Path,
    *,
    running: set[str],
    existing: set[str],
) -> None:
    if not getattr(client, "dry_run", False):
        config_dir.mkdir(parents=True, exist_ok=True)
        write_coredns_config(
            config_dir,
            services=[],
            inspected_services={},
        )
    if dns_service.container_name in running:
        inspected = inspect_container(client, dns_service.container_name)
        if not _image_matches(inspected.image, dns_service.image):
            client.run(["rm", "--force", dns_service.container_name])
            client.run(["run", *dns_service.run_args])
        return
    if dns_service.container_name in existing:
        inspected = inspect_container(client, dns_service.container_name)
        if not _image_matches(inspected.image, dns_service.image):
            client.run(["rm", "--force", dns_service.container_name])
            client.run(["run", *dns_service.run_args])
            return
        client.run(["start", dns_service.container_name])
        return
    client.run(["run", *dns_service.run_args])


def assign_dns_servers(
    services: list[ServicePlan],
    dns_sidecar: InspectedContainer,
) -> None:
    for service in services:
        service.dns_servers = []
        for network_name in _network_match_names(service):
            dns_ip = dns_sidecar.ip_for_network(network_name)
            if dns_ip:
                service.dns_servers = [dns_ip]
                break
        if not service.dns_servers:
            raise ContainerRuntimeError(
                "DNS sidecar has no IPv4 address on any network used by "
                f"service {service.service_name}"
            )


def assign_dry_run_dns_servers(services: list[ServicePlan], dns_service: ServicePlan) -> None:
    for service in services:
        network_name = service.network_names[0] if service.network_names else "default"
        service.dns_servers = [f"<{dns_service.container_name}:{network_name}>"]


def inspect_container(client: ContainerClient, container_name: str) -> InspectedContainer:
    result = client.run(["inspect", container_name], capture_output=True)
    output = result.stdout if result else "{}"
    try:
        raw = json.loads(output or "{}")
    except json.JSONDecodeError as exc:
        raise ContainerRuntimeError(f"Invalid JSON from container inspect: {exc}") from exc
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        raise ContainerRuntimeError("Expected container inspect output to be an object")
    return InspectedContainer(
        name=_container_name(raw) or container_name,
        networks=_container_networks(raw),
        image=_container_image(raw),
    )


def write_coredns_config(
    config_dir: Path,
    *,
    services: list[ServicePlan],
    inspected_services: dict[str, InspectedContainer],
) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(config_dir / "Corefile", render_corefile())
    records = []
    for service in services:
        inspected = inspected_services.get(service.container_name)
        if not inspected:
            continue
        ip = _service_ip(service, inspected)
        if not ip:
            continue
        aliases = _service_aliases(service)
        if aliases:
            records.append(HostsRecord(ip=ip, aliases=aliases))
    _atomic_write(
        config_dir / "hosts",
        render_hosts_file(CoreDnsConfig(records=records)),
    )


def render_corefile() -> str:
    return _template_env().get_template("Corefile.j2").render()


def render_hosts_file(config: CoreDnsConfig) -> str:
    template = _template_env().get_template("hosts.j2")
    return template.render(
        records=config.records,
    )


def remove_dns_sidecar_if_unused(
    client: ContainerClient,
    dns_service: ServicePlan,
    remaining_services: list[ServicePlan],
) -> None:
    if remaining_services:
        return
    client.run(["rm", "--force", dns_service.container_name])


def _dns_network_attachments(plan: AppPlan) -> list[NetworkAttachment]:
    attachments: dict[str, NetworkAttachment] = {}
    for service in plan.services:
        for attachment in service.network_attachments:
            attachments.setdefault(
                attachment.runtime_name,
                NetworkAttachment(
                    key=attachment.key,
                    runtime_name=attachment.runtime_name,
                    aliases=[],
                ),
            )
    for network_name in plan.network_names:
        attachments.setdefault(
            network_name,
            NetworkAttachment(key=network_name, runtime_name=network_name, aliases=[]),
        )
    return list(attachments.values())


def _service_ip(service: ServicePlan, inspected: InspectedContainer) -> str | None:
    for network_name in _network_match_names(service):
        network = inspected.networks.get(network_name)
        if network and network.ipv4:
            return network.ipv4[0]
    return None


def _network_match_names(service: ServicePlan) -> list[str]:
    names: list[str] = []
    for attachment in service.network_attachments:
        names.extend([attachment.runtime_name, attachment.key])
    return list(dict.fromkeys(name for name in names if name))


def _service_aliases(service: ServicePlan) -> list[str]:
    aliases: list[str] = []
    for attachment in service.network_attachments:
        aliases.extend(attachment.aliases)
    return list(dict.fromkeys(alias.lower() for alias in aliases if alias))


def _atomic_write(path: Path, value: str) -> None:
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(value)
    tmp_path.replace(path)


def _template_env() -> Environment:
    template_dir = resources.files("apple_compose.resources.dns_templates")
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        keep_trailing_newline=True,
    )


def _container_name(raw: dict[str, Any]) -> str | None:
    configuration = raw.get("configuration")
    if isinstance(configuration, dict) and isinstance(configuration.get("id"), str):
        return configuration["id"]
    for key in ("id", "name"):
        if isinstance(raw.get(key), str):
            return raw[key]
    return None


def _container_image(raw: dict[str, Any]) -> str | None:
    configuration = raw.get("configuration")
    if not isinstance(configuration, dict):
        return None
    image = configuration.get("image")
    if isinstance(image, str):
        return image
    if isinstance(image, dict):
        reference = image.get("reference")
        if isinstance(reference, str):
            return reference
    return None


def _image_matches(actual: str | None, expected: str) -> bool:
    if not actual:
        return True
    return _normalize_image_name(actual) == _normalize_image_name(expected)


def _normalize_image_name(value: str) -> str:
    for prefix in ("docker.io/library/", "docker.io/"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def _container_networks(raw: dict[str, Any]) -> dict[str, NetworkAddress]:
    networks: dict[str, NetworkAddress] = {}
    raw_networks = raw.get("networks") or raw.get("networkSettings") or raw.get("Networks")
    if isinstance(raw_networks, dict):
        for name, value in raw_networks.items():
            network = _network_address(str(name), value)
            if network:
                networks[network.network_name] = network
    elif isinstance(raw_networks, list):
        for value in raw_networks:
            name = _network_name(value)
            network = _network_address(name, value)
            if network:
                networks[network.network_name] = network
    return networks


def _network_name(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in ("network", "name", "networkName", "id"):
        if isinstance(value.get(key), str):
            return value[key]
    return None


def _network_address(name: str | None, value: Any) -> NetworkAddress | None:
    if not name or not isinstance(value, dict):
        return None
    ipv4: list[str] = []
    ipv6: list[str] = []
    for candidate in _walk_address_strings(value):
        parsed = _parse_ip(candidate)
        if not parsed:
            continue
        if parsed.version == 4:
            ipv4.append(str(parsed))
        else:
            ipv6.append(str(parsed))
    return NetworkAddress(
        network_name=name,
        ipv4=list(dict.fromkeys(ipv4)),
        ipv6=list(dict.fromkeys(ipv6)),
    )


def _walk_address_strings(value: Any, *, key: str | None = None) -> list[str]:
    address_keys = {
        "address",
        "addresses",
        "addr",
        "ip",
        "ips",
        "ipaddress",
        "ip_address",
        "ipv4",
        "ipv4address",
        "ipv4_address",
        "ipv6",
        "ipv6address",
        "ipv6_address",
    }
    if isinstance(value, str):
        if key and key.lower() in address_keys:
            return [value]
        return []
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_walk_address_strings(item, key=key))
        return values
    if isinstance(value, dict):
        values = []
        for item_key, item in value.items():
            values.extend(_walk_address_strings(item, key=str(item_key)))
        return values
    return []


def _parse_ip(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    if not value or value == "0.0.0.0":
        return None
    candidate = value.split("/", 1)[0]
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None
