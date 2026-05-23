from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console

from apple_compose.container_cli import ContainerClient
from apple_compose.models import ComposeConfig, ContainerSnapshot
from apple_compose.planner import AppPlan, create_plan
from apple_compose.runtime import load_container_snapshot

console = Console()


@dataclass
class CliContext:
    file: Path
    env_file: Path | None
    project_name: str | None
    verbose: bool
    dry_run: bool
    _container_snapshots: dict[str, ContainerSnapshot] = field(default_factory=dict, init=False)

    def load_compose(self) -> ComposeConfig:
        compose = ComposeConfig.from_file(self.file)
        for warning in compose.warnings:
            console.print(f"Warning: {warning}", style="yellow")
        return compose

    def load_plan(
        self,
        *,
        services: list[str] | None = None,
        detach: bool = True,
        include_builds: bool = False,
        no_cache: bool = False,
    ) -> AppPlan:
        compose = self.load_compose()
        return create_plan(
            compose,
            compose_path=self.file,
            cwd=self.file.parent,
            project_name=self.project_name,
            requested_services=services or [],
            env_file=self.env_file if self.env_file else self.file.parent / ".env",
            env_file_required=self.env_file is not None,
            detach=detach,
            include_builds=include_builds,
            no_cache=no_cache,
        )

    def container_snapshot(self, client: ContainerClient, plan: AppPlan) -> ContainerSnapshot:
        if plan.project_name not in self._container_snapshots:
            self._container_snapshots[plan.project_name] = load_container_snapshot(
                client,
                project_name=plan.project_name,
            )
        return self._container_snapshots[plan.project_name]
