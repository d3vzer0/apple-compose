import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.planner import resolve_project_name


@app.command(name="volumes")
def volumes(ctx: typer.Context) -> None:
    """Show volumes declared by the current Compose file."""
    state: CliContext = ctx.obj
    compose = state.load_compose()
    project_name = resolve_project_name(compose, state.file.parent, state.project_name)

    table = Table("Volume", "Runtime Name", "External")
    for name, config in compose.volumes.items():
        runtime_name = compose.resolve_volume_source(name, state.file.parent, project_name)
        external = "yes" if config and config.external else "no"
        table.add_row(name, runtime_name, external)
    console.print(table)
