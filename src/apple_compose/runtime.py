from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from apple_compose.container_cli import ContainerClient
from apple_compose.models import ContainerList

if TYPE_CHECKING:
    from apple_compose.planner import ServicePlan


@dataclass
class ContainerSnapshot:
    running: set[str]
    existing: set[str]
    running_by_service: dict[str, str]
    existing_by_service: dict[str, str]

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


def load_container_snapshot(client: ContainerClient, *, project_name: str) -> ContainerSnapshot:
    running_result = client.run(["ls", "--format", "json"], capture_output=True)
    existing_result = client.run(["ls", "--all", "--format", "json"], capture_output=True)

    running_list = ContainerList.from_command_output(running_result.stdout if running_result else None)
    existing_list = ContainerList.from_command_output(existing_result.stdout if existing_result else None)
    return ContainerSnapshot(
        running=running_list.ids,
        existing=existing_list.ids,
        running_by_service=running_list.ids_by_service(project_name=project_name),
        existing_by_service=existing_list.ids_by_service(project_name=project_name),
    )
