import json
from collections.abc import Iterable
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apple_compose.errors import ContainerRuntimeError
from apple_compose.labels import (
    APPLE_COMPOSE_CREATED_BY_LABEL,
    APPLE_COMPOSE_CREATED_BY_VALUE,
    DOCKER_COMPOSE_PROJECT_LABEL,
    DOCKER_COMPOSE_SERVICE_LABEL,
    DOCKER_COMPOSE_ONEOFF_LABEL,
)

if TYPE_CHECKING:
    from apple_compose.planner import ServicePlan


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
            if labels.get(DOCKER_COMPOSE_ONEOFF_LABEL, "").lower() == "true":
                continue

            service_name = labels.get(DOCKER_COMPOSE_SERVICE_LABEL)
            if service_name:
                ids[service_name] = configuration.id
        return ids

    def project_summaries(self) -> list["ContainerProjectSummary"]:
        projects: dict[str, ContainerProjectSummary] = {}
        for container in self.containers:
            configuration = container.configuration
            if not configuration:
                continue

            labels = configuration.labels
            if labels.get(APPLE_COMPOSE_CREATED_BY_LABEL) != APPLE_COMPOSE_CREATED_BY_VALUE:
                continue

            project_name = labels.get(DOCKER_COMPOSE_PROJECT_LABEL)
            if not project_name:
                continue

            summary = projects.setdefault(
                project_name,
                ContainerProjectSummary(project=project_name, containers=0, running=0),
            )
            summary.containers += 1
            if container.status == "running":
                summary.running += 1
        return sorted(projects.values(), key=lambda summary: summary.project)


class ContainerProjectSummary(BaseModel):
    project: str
    containers: int
    running: int


class ContainerSnapshot(BaseModel):
    running: set[str]
    existing: set[str]
    running_by_service: dict[str, str]
    existing_by_service: dict[str, str]

    @classmethod
    def from_command_outputs(
        cls,
        *,
        running_output: str | None,
        existing_output: str | None,
        project_name: str,
    ) -> Self:
        running = ContainerList.from_command_output(running_output)
        existing = ContainerList.from_command_output(existing_output)
        return cls(
            running=running.ids,
            existing=existing.ids,
            running_by_service=running.ids_by_service(project_name=project_name),
            existing_by_service=existing.ids_by_service(project_name=project_name),
        )

    def filter_running(self, names: Iterable[str]) -> list[str]:
        return [name for name in names if name in self.running]

    def filter_existing(self, names: Iterable[str]) -> list[str]:
        return [name for name in names if name in self.existing]

    def running_for_services(self, services: Iterable["ServicePlan"]) -> list[str]:
        return self._containers_for_services(
            services,
            containers=self.running,
            containers_by_service=self.running_by_service,
        )

    def existing_for_services(self, services: Iterable["ServicePlan"]) -> list[str]:
        return self._containers_for_services(
            services,
            containers=self.existing,
            containers_by_service=self.existing_by_service,
        )

    def _containers_for_services(
        self,
        services: Iterable["ServicePlan"],
        *,
        containers: set[str],
        containers_by_service: dict[str, str],
    ) -> list[str]:
        names: list[str] = []
        for service in services:
            labeled_container = containers_by_service.get(service.service_name)
            if labeled_container:
                names.append(labeled_container)
            elif service.container_name in containers:
                names.append(service.container_name)
        return names
