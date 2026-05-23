from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="stop")
def stop(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to stop.")] = None,
    signal: Annotated[
        str | None,
        typer.Option("--signal", help="Signal to send to containers."),
    ] = None,
    time: Annotated[
        int | None,
        typer.Option("--time", help="Seconds to wait before killing containers."),
    ] = None,
) -> None:
    """Stop running services."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    args = ["stop"]
    if signal:
        args.extend(["--signal", signal])
    if time is not None:
        args.extend(["--time", str(time)])
    args.extend(service.container_name for service in reversed(plan.services))

    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    container_client.run(args)
