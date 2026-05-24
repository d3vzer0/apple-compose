from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="pull")
def pull(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to pull images for.")] = None,
) -> None:
    """Pull service images."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )

    pulled = False
    for service in plan.services:
        if service.service.image:
            container_client.run(["image", "pull", service.service.image])
            pulled = True
    if not pulled:
        console.print("No pullable services selected.")
