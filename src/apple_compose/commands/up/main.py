from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.container_cli import ContainerClient
from apple_compose.dns import (
    assign_dns_servers,
    assign_dry_run_dns_servers,
    create_dns_service,
    dns_config_dir,
    ensure_dns_sidecar,
    inspect_container,
    write_coredns_config,
)
from apple_compose.errors import PlanningError
from apple_compose.models import ContainerSnapshot
from apple_compose.planner import ServicePlan


@app.command(name="up")
def up(
    ctx: typer.Context,
    services: Annotated[
        list[str] | None, typer.Argument(help="Services to start.")
    ] = None,
    detach: Annotated[
        bool,
        typer.Option("--detach", "-d", help="Run containers detached."),
    ] = False,
    build: Annotated[
        bool, typer.Option("--build", help="Build images before starting.")
    ] = False,
    no_cache: Annotated[
        bool, typer.Option("--no-cache", help="Build without cache.")
    ] = False,
) -> None:
    """Create and start services."""
    state: CliContext = ctx.obj
    plan = state.load_plan(
        services=services,
        detach=detach,
        include_builds=build,
        no_cache=no_cache,
    )
    container_client = ContainerClient(
        dry_run=state.dry_run,
        verbose=state.verbose,
        console=console,
    )
    dns_config = dns_config_dir(state.file, plan.project_name)
    dns_service = create_dns_service(plan, dns_config)
    snapshot = None
    if not state.dry_run:
        snapshot = state.container_snapshot(container_client, plan)
        for service in plan.services:
            _ensure_planned_name_available(service, snapshot)

    existing_networks = set()
    if not state.dry_run:
        existing_networks = state.network_snapshot(container_client).existing
    for network_name in plan.network_names:
        if network_name in existing_networks:
            continue
        container_client.run(["network", "create", network_name])
    if state.dry_run:
        ensure_dns_sidecar(
            container_client,
            dns_service,
            dns_config,
            running=set(),
            existing=set(),
        )
        assign_dry_run_dns_servers(plan.services, dns_service)
    else:
        assert snapshot is not None
        ensure_dns_sidecar(
            container_client,
            dns_service,
            dns_config,
            running=snapshot.running,
            existing=snapshot.existing,
        )
        dns_sidecar = inspect_container(container_client, dns_service.container_name)
        assign_dns_servers(plan.services, dns_sidecar)
        inspected_services = {}
        write_coredns_config(
            dns_config,
            services=plan.services,
            inspected_services=inspected_services,
        )
    for service in plan.services:
        if service.build_args:
            container_client.run(["build", *service.build_args])
    for service in plan.services:
        if snapshot:
            running_name = snapshot.running_by_service.get(service.service_name)
            if running_name:
                inspected_services[service.container_name] = inspect_container(
                    container_client,
                    running_name,
                )
                write_coredns_config(
                    dns_config,
                    services=plan.services,
                    inspected_services=inspected_services,
                )
                continue
            existing_name = snapshot.existing_by_service.get(service.service_name)
            if existing_name:
                container_client.run(["start", existing_name])
                inspected_services[service.container_name] = inspect_container(
                    container_client,
                    existing_name,
                )
                write_coredns_config(
                    dns_config,
                    services=plan.services,
                    inspected_services=inspected_services,
                )
                continue
        container_client.run(["run", *service.run_args])
        if not state.dry_run:
            inspected_services[service.container_name] = inspect_container(
                container_client,
                service.container_name,
            )
            write_coredns_config(
                dns_config,
                services=plan.services,
                inspected_services=inspected_services,
            )


def _ensure_planned_name_available(
    service: ServicePlan, snapshot: ContainerSnapshot
) -> None:
    existing_name = snapshot.existing_by_service.get(service.service_name)
    if service.container_name in snapshot.existing and existing_name != service.container_name:
        raise PlanningError(
            "Container already exists but is not managed by apple-compose: "
            f"{service.container_name}"
        )
