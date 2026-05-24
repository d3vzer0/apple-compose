from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.errors import PlanningError
from apple_compose.planner import ServicePlan


@app.command(
    name="run",
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    },
)
def run(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="Service to run once.")],
    command: Annotated[
        list[str] | None,
        typer.Argument(help="Command to run instead of the service default."),
    ] = None,
    remove: Annotated[
        bool,
        typer.Option("--rm", "--remove", help="Remove the container after it stops."),
    ] = False,
) -> None:
    """Run a one-off service container. Use -- before command args."""
    state: CliContext = ctx.obj
    command = command or []
    if command and command[0] != "--":
        raise PlanningError("run command must follow --")
    command = command[1:]
    plan = state.load_plan(services=[service], detach=False, include_dependencies=False)
    service_plan = _selected_service_plan(plan.services, service)

    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    container_client.run(["run", *_one_off_run_args(service_plan, remove=remove, command=command)])


def _one_off_run_args(
    service: ServicePlan,
    *,
    remove: bool,
    command: list[str],
) -> list[str]:
    args = _without_name(service.run_args)
    separator_index = args.index("--")
    args[separator_index:separator_index] = ["--label", "com.docker.compose.oneoff=True"]
    separator_index += 2
    if remove:
        args.insert(separator_index, "--rm")
        separator_index += 1
    if command:
        args = args[: separator_index + 2] + command
    return args


def _without_name(args: list[str]) -> list[str]:
    output: list[str] = []
    index = 0
    while index < len(args):
        if args[index] == "--":
            output.extend(args[index:])
            break
        if args[index] == "--name":
            index += 2
            continue
        output.append(args[index])
        index += 1
    return output


def _selected_service_plan(services: list[ServicePlan], service_name: str) -> ServicePlan:
    for service in services:
        if service.service_name == service_name:
            return service
    raise PlanningError(f"Unknown service: {service_name}")
