from typing import Any

from pydantic import BaseModel, model_validator


class PortMapping(BaseModel):
    host_ip: str = "0.0.0.0"
    published: str
    target: str
    protocol: str | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_compose_port(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            if {"host_ip", "published", "target"}.issubset(value):
                return value
            raise ValueError("Long port syntax is not supported yet")
        if isinstance(value, str | int):
            return _parse_compose_port(value)
        raise ValueError(f"Unsupported port syntax: {value}")

    def to_container_arg(self) -> str:
        protocol = f"/{self.protocol}" if self.protocol else ""
        return f"{self.host_ip}:{self.published}:{self.target}{protocol}"


def _parse_compose_port(port: str | int) -> dict[str, str | None]:
    value = str(port)
    protocol = None
    if "/" in value:
        value, protocol = value.rsplit("/", 1)

    parts = value.split(":")
    if len(parts) == 1:
        host_ip = "0.0.0.0"
        published = target = parts[0]
    elif len(parts) == 2:
        host_ip = "0.0.0.0"
        published, target = parts
    elif len(parts) == 3:
        host_ip, published, target = parts
    else:
        raise ValueError(f"Unsupported port syntax: {port}")

    if not published or not target:
        raise ValueError(f"Unsupported port syntax: {port}")
    return {"host_ip": host_ip, "published": published, "target": target, "protocol": protocol}
