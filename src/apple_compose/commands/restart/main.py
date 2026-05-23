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
    stop_args = ["stop"]
    if signal:
        stop_args.extend(["--signal", signal])
    if time is not None:
        stop_args.extend(["--time", str(time)])
    stop_args.extend(service.container_name for service in reversed(plan.services))

    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    container_client.run(stop_args)
    for service in plan.services:
        container_client.run(["start", service.container_name])
