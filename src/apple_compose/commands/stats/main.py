from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient


@app.command(name="stats")
def stats(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to show stats for.")] = None,
    output_format: Annotated[
        str | None,
        typer.Option("--format", help="Output format passed to container stats."),
    ] = None,
    no_stream: Annotated[
        bool,
        typer.Option("--no-stream", help="Disable streaming stats."),
    ] = False,
) -> None:
    """Display service resource usage statistics."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    args = ["stats"]
    args.extend(service.container_name for service in plan.services)
    if output_format:
        args.extend(["--format", output_format])
    if no_stream:
        args.append("--no-stream")

    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    container_client.run(args)
