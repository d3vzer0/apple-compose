from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="build")
def build(
    ctx: typer.Context,
    services: Annotated[
        list[str] | None, typer.Argument(help="Services to build_.")
    ] = None,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Build without cache.")
    ] = False,
) -> None:
    """Build service images."""
    state: CliContext = ctx.obj
    plan = state.load_plan(
        services=services,
        detach=True,
        include_builds=True,
        no_cache=no_cache,
    )
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    built = False
    for service in plan.services:
        if service.build_args:
            container_client.run(["build", *service.build_args])
            built = True
    if not built:
        console.print("No buildable services selected.")
