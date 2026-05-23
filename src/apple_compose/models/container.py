import json
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apple_compose.errors import ContainerRuntimeError
from apple_compose.labels import (
    APPLE_COMPOSE_CREATED_BY_LABEL,
    APPLE_COMPOSE_CREATED_BY_VALUE,
    DOCKER_COMPOSE_PROJECT_LABEL,
    DOCKER_COMPOSE_SERVICE_LABEL,
)


class ContainerConfiguration(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class ContainerListEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str | None = None
    configuration: ContainerConfiguration | None = None


class ContainerList(BaseModel):
    model_config = ConfigDict(extra="allow")

    containers: list[ContainerListEntry]

    @classmethod
    def from_json(cls, value: str) -> Self:
        try:
            raw = json.loads(value or "[]")
        except json.JSONDecodeError as exc:
            raise ContainerRuntimeError(f"Invalid JSON from container CLI: {exc}") from exc

        if not isinstance(raw, list):
            raise ContainerRuntimeError("Expected container CLI JSON output to be a list")

        try:
            return cls.model_validate({"containers": raw})
        except ValidationError as exc:
            raise ContainerRuntimeError(str(exc)) from exc

    @classmethod
    def from_command_output(cls, output: str | None) -> Self:
        return cls.from_json(output or "[]")

    @property
    def ids(self) -> set[str]:
        ids: set[str] = set()
        for container in self.containers:
            if container.configuration and container.configuration.id:
                ids.add(container.configuration.id)
        return ids

    def ids_by_service(self, *, project_name: str) -> dict[str, str]:
        ids: dict[str, str] = {}
        for container in self.containers:
            configuration = container.configuration
            if not configuration or not configuration.id:
                continue

            labels = configuration.labels
            if labels.get(APPLE_COMPOSE_CREATED_BY_LABEL) != APPLE_COMPOSE_CREATED_BY_VALUE:
                continue
            if labels.get(DOCKER_COMPOSE_PROJECT_LABEL) != project_name:
                continue

            service_name = labels.get(DOCKER_COMPOSE_SERVICE_LABEL)
            if service_name:
                ids[service_name] = configuration.id
        return ids
