import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.models import ContainerList


@app.command(name="ls")
def ls(ctx: typer.Context) -> None:
    """List apple-compose projects."""
    state: CliContext = ctx.obj
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    result = container_client.run(["ls", "--all", "--format", "json"], capture_output=True)
    if result is None:
        return

    table = Table("Project", "Containers", "Running")
    for project in ContainerList.from_command_output(result.stdout).project_summaries():
        table.add_row(project.project, str(project.containers), str(project.running))
    console.print(table)
