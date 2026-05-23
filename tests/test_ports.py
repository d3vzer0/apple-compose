import pytest

from apple_compose.models import PortMapping, ServiceConfig


@pytest.mark.parametrize(
    ("input_value", "expected"),
    [
        ("80", "0.0.0.0:80:80"),
        ("8080:80", "0.0.0.0:8080:80"),
        ("127.0.0.1:8080:80", "127.0.0.1:8080:80"),
        ("8080:80/udp", "0.0.0.0:8080:80/udp"),
    ],
)
def test_port_mapping_model_validate(input_value: str, expected: str) -> None:
    assert PortMapping.model_validate(input_value).to_container_arg() == expected


def test_port_mapping_extracts_dash_prefixed_value() -> None:
    port = PortMapping.model_validate("-pwn")

    assert port.host_ip == "0.0.0.0"
    assert port.published == "-pwn"
    assert port.target == "-pwn"
    assert port.to_container_arg() == "0.0.0.0:-pwn:-pwn"


@pytest.mark.parametrize("input_value", ["0:80", "65536:80", "8080:0", "8080:65536"])
def test_port_mapping_extracts_invalid_port_ranges(input_value: str) -> None:
    assert PortMapping.model_validate(input_value).to_container_arg()


def test_port_mapping_extracts_invalid_host_ip() -> None:
    port = PortMapping.model_validate("not-an-ip:8080:80")

    assert port.host_ip == "not-an-ip"
    assert port.published == "8080"
    assert port.target == "80"


def test_port_mapping_extracts_invalid_protocol() -> None:
    port = PortMapping.model_validate("8080:80/sctp")

    assert port.protocol == "sctp"
    assert port.to_container_arg() == "0.0.0.0:8080:80/sctp"


def test_port_mapping_rejects_unsupported_shape() -> None:
    with pytest.raises(ValueError):
        PortMapping.model_validate("1:2:3:4")


def test_service_config_normalizes_ports() -> None:
    service = ServiceConfig.model_validate({"image": "nginx", "ports": ["8080:80"]})

    assert service.ports[0].to_container_arg() == "0.0.0.0:8080:80"
