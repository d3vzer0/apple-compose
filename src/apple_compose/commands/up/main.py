from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.errors import PlanningError
from apple_compose.models import ContainerSnapshot
from apple_compose.planner import ServicePlan


@app.command(name="up")
def up(
    ctx: typer.Context,
    services: Annotated[
        list[str] | None, typer.Argument(help="Services to start.")
    ] = None,
    detach: Annotated[
        bool,
        typer.Option("--detach", "-d", help="Run containers detached."),
    ] = False,
    build: Annotated[
        bool, typer.Option("--build", help="Build images before starting.")
    ] = False,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Build without cache.")
    ] = False,
) -> None:
    """Create and start services."""
    state: CliContext = ctx.obj
    plan = state.load_plan(
        services=services,
        detach=detach,
        include_builds=build,
        no_cache=no_cache,
    )
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    snapshot = None
    if not state.dry_run:
        snapshot = state.container_snapshot(container_client, plan)
        for service in plan.services:
            _ensure_planned_name_available(service, snapshot)

    for network_name in plan.network_names:
        container_client.run(["network", "create", network_name])
    for service in plan.services:
        if service.build_args:
            container_client.run(["build", *service.build_args])
    for service in plan.services:
        if snapshot:
            running_name = snapshot.running_by_service.get(service.service_name)
            if running_name:
                continue
            existing_name = snapshot.existing_by_service.get(service.service_name)
            if existing_name:
                container_client.run(["start", existing_name])
                continue
        container_client.run(["run", *service.run_args])


def _ensure_planned_name_available(
    service: ServicePlan, snapshot: ContainerSnapshot
) -> None:
    existing_name = snapshot.existing_by_service.get(service.service_name)
    if service.container_name in snapshot.existing and existing_name != service.container_name:
        raise PlanningError(
            "Container already exists but is not managed by apple-compose: "
            f"{service.container_name}"
        )
