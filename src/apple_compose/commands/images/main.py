from typing import Annotated

import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console


@app.command(name="images")
def images(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to show images for.")] = None,
) -> None:
    """Show images referenced by the current Compose file."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)

    table = Table("Service", "Image")
    for service in plan.services:
        table.add_row(service.service_name, service.image)
    console.print(table)
