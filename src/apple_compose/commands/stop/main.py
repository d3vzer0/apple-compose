from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.dns import create_dns_service, dns_config_dir


@app.command(name="stop")
def stop(
    ctx: typer.Context,
    services: Annotated[list[str] | None, typer.Argument(help="Services to stop.")] = None,
    signal: Annotated[
        str | None,
        typer.Option("--signal", help="Signal to send to containers."),
    ] = None,
    time: Annotated[
        int | None,
        typer.Option("--time", help="Seconds to wait before killing containers."),
    ] = None,
) -> None:
    """Stop running services."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True, include_dependencies=False)
    all_services_plan = plan if services is None else state.load_plan(detach=True)
    dns_config = dns_config_dir(state.file, all_services_plan.project_name)
    dns_service = create_dns_service(all_services_plan, dns_config)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    planned_services = list(reversed(plan.services))
    container_names = [service.container_name for service in planned_services]
    stop_dns = services is None
    if not state.dry_run:
        snapshot = state.container_snapshot(container_client, all_services_plan)
        container_names = snapshot.running_for_services(planned_services)
        if stop_dns and dns_service.container_name in snapshot.running:
            container_names.append(dns_service.container_name)
    elif stop_dns:
        container_names.append(dns_service.container_name)
    if not container_names:
        console.print("No running services to stop.")
        return

    args = ["stop"]
    if signal:
        args.extend(["--signal", signal])
    if time is not None:
        args.extend(["--time", str(time)])
    args.extend(container_names)

    container_client.run(args)
