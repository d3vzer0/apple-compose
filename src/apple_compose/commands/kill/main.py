from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="kill")
def kill(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to kill.")] = None,
    signal: Annotated[
        str | None,
        typer.Option("--signal", "-s", help="Signal to send to containers."),
    ] = None,
) -> None:
    """Kill running service containers."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    planned_services = list(reversed(plan.services))
    container_names = [service.container_name for service in planned_services]
    if not state.dry_run:
        container_names = state.container_snapshot(container_client, plan).running_for_services(
            planned_services
        )
    if not container_names:
        console.print("No running services to kill.")
        return

    args = ["kill"]
    if signal:
        args.extend(["--signal", signal])
    args.extend(container_names)
    container_client.run(args)
