from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.dns import (
    create_dns_service,
    dns_config_dir,
    inspect_container,
    write_coredns_config,
)


@app.command(name="down")
def down(
    ctx: typer.Context,
    services: Annotated[
        list[str] | None,
        typer.Argument(help="Services to remove."),
    ] = None,
) -> None:
    """Remove service containers."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=services, detach=True, include_dependencies=False)
    all_services_plan = state.load_plan(detach=True)
    dns_config = dns_config_dir(state.file, all_services_plan.project_name)
    dns_service = create_dns_service(all_services_plan, dns_config)
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    planned_services = list(reversed(plan.services))
    container_names = [service.container_name for service in planned_services]
    snapshot = None
    if not state.dry_run:
        snapshot = state.container_snapshot(container_client, all_services_plan)
        container_names = snapshot.existing_for_services(planned_services)
    if not container_names:
        console.print("No existing services to remove.")
        return

    for container_name in container_names:
        container_client.run(["rm", "--force", container_name])

    if state.dry_run or snapshot is None:
        return

    removed_services = {service.service_name for service in planned_services}
    remaining_services = [
        service
        for service in all_services_plan.services
        if service.service_name not in removed_services
        and service.service_name in snapshot.existing_by_service
    ]
    if not remaining_services:
        if dns_service.container_name in snapshot.existing:
            container_client.run(["rm", "--force", dns_service.container_name])
        return

    if dns_service.container_name not in snapshot.existing:
        return

    inspected_services = {
        service.container_name: inspect_container(
            container_client,
            snapshot.existing_by_service[service.service_name],
        )
        for service in remaining_services
    }
    write_coredns_config(
        dns_config,
        services=remaining_services,
        inspected_services=inspected_services,
    )
