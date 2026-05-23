from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.errors import PlanningError


@app.command(name="logs")
def logs(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to show logs for.")] = None,
    boot: Annotated[bool, typer.Option("--boot", help="Show boot log instead of stdio.")] = False,
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="Follow log output."),
    ] = False,
    n: Annotated[int | None, typer.Option("-n", help="Number of log lines to show.")] = None,
) -> None:
    """Fetch service logs."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True)
    if follow and len(plan.services) != 1:
        raise PlanningError("logs --follow requires exactly one service")

    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    for service in plan.services:
        args = ["logs"]
        if boot:
            args.append("--boot")
        if follow:
            args.append("--follow")
        if n is not None:
            args.extend(["-n", str(n)])
        args.append(service.container_name)
        container_client.run(args)
