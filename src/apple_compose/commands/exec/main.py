from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.errors import PlanningError


@app.command(
    name="exec",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def exec_(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="Service to execute the command in.")],
    detach: Annotated[bool, typer.Option("--detach", "-d", help="Run the command detached.")] = False,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Keep stdin open."),
    ] = False,
    tty: Annotated[bool, typer.Option("--tty", "-t", help="Allocate a TTY.")] = False,
    user: Annotated[
        str | None,
        typer.Option("--user", "-u", help="User to run as."),
    ] = None,
    workdir: Annotated[
        str | None,
        typer.Option("--workdir", "-w", "--cwd", help="Working directory in the container."),
    ] = None,
) -> None:
    """Execute a command in a running service container."""
    state: CliContext = ctx.obj
    command = list(ctx.args)
    if not command:
        raise PlanningError("exec requires a command")

    plan = state.load_plan(services=[service], detach=True)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    container_names = [plan.services[0].container_name]
    if not state.dry_run:
        container_names = state.container_snapshot(container_client, plan).running_for_services(
            plan.services
        )
    if not container_names:
        raise PlanningError(f"Service is not running: {service}")

    args = ["exec"]
    if detach:
        args.append("--detach")
    if interactive:
        args.append("--interactive")
    if tty:
        args.append("--tty")
    if user:
        args.extend(["--user", user])
    if workdir:
        args.extend(["--workdir", workdir])
    args.append(container_names[0])
    args.extend(command)
    container_client.run(args)
