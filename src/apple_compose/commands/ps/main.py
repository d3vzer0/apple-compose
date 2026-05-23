import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console


@app.command(name="ps")
def ps(
    ctx: typer.Context,
) -> None:
    """Show planned services from the current Compose file."""
    state: CliContext = ctx.obj
    plan = state.load_plan(detach=True)
    table = Table("Service", "Container", "Image")
    for service in plan.services:
        table.add_row(service.service_name, service.container_name, service.image)
    console.print(table)
