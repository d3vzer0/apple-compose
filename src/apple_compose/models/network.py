import json
from typing import Self

from pydantic import BaseModel, ConfigDict, ValidationError

from apple_compose.errors import ContainerRuntimeError


class NetworkConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    external: bool = False

    def runtime_name(self, project_name: str, key: str) -> str:
        if self.name:
            return self.name
        return f"{project_name}-{key}"


class NetworkListConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None


class NetworkListEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    config: NetworkListConfig | None = None
    state: str | None = None

    @property
    def runtime_name(self) -> str | None:
        if self.id:
            return self.id
        if self.config:
            return self.config.id
        return None


class NetworkList(BaseModel):
    model_config = ConfigDict(extra="allow")

    networks: list[NetworkListEntry]

    @classmethod
    def from_json(cls, value: str) -> Self:
        try:
            raw = json.loads(value or "[]")
        except json.JSONDecodeError as exc:
            raise ContainerRuntimeError(f"Invalid JSON from container network CLI: {exc}") from exc

        if not isinstance(raw, list):
            raise ContainerRuntimeError("Expected container network CLI JSON output to be a list")

        try:
            return cls.model_validate({"networks": raw})
        except ValidationError as exc:
            raise ContainerRuntimeError(str(exc)) from exc

    @classmethod
    def from_command_output(cls, output: str | None) -> Self:
        return cls.from_json(output or "[]")

    @property
    def ids(self) -> set[str]:
        return {
            network.runtime_name
            for network in self.networks
            if network.runtime_name
        }


class NetworkSnapshot(BaseModel):
    existing: set[str]

    @classmethod
    def from_command_output(cls, output: str | None) -> Self:
        return cls(existing=NetworkList.from_command_output(output).ids)
