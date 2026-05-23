from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="restart")
def restart(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to restart.")] = None,
    signal: Annotated[
        str | None,
        typer.Option("--signal", help="Signal to send when stopping containers."),
    ] = None,
    time: Annotated[
        int | None,
        typer.Option("--time", help="Seconds to wait before killing containers."),
    ] = None,
) -> None:
    """Restart services."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )

    stop_services = list(reversed(plan.services))
    start_services = plan.services
    stop_names = [service.container_name for service in stop_services]
    start_names = [service.container_name for service in start_services]
    if not state.dry_run:
        snapshot = state.container_snapshot(container_client, plan)
        stop_names = snapshot.running_for_services(stop_services)
        start_names = snapshot.existing_for_services(start_services)
    if not start_names:
        console.print("No existing services to restart.")
        return

    stop_args = ["stop"]
    if signal:
        stop_args.extend(["--signal", signal])
    if time is not None:
        stop_args.extend(["--time", str(time)])
    stop_args.extend(stop_names)

    if stop_names:
        container_client.run(stop_args)
    for container_name in start_names:
        container_client.run(["start", container_name])
