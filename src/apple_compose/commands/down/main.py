from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="down")
def down(
    ctx: typer.Context,
    services: Annotated[
        list[str] | None,
        typer.Argument(help="Services to stop and remove."),
    ] = None,
) -> None:
    """Stop and remove services."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    for service in reversed(plan.services):
        container_client.run(["rm", "--force", service.container_name])
