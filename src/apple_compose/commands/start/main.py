from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="start")
def start(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to start.")] = None,
) -> None:
    """Start existing service containers."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True, include_dependencies=False)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    container_names = [service.container_name for service in plan.services]
    if not state.dry_run:
        container_names = state.container_snapshot(container_client, plan).existing_for_services(
            plan.services
        )
    if not container_names:
        console.print("No existing services to start.")
        return

    for container_name in container_names:
        container_client.run(["start", container_name])
