from typing import Annotated

import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.errors import PlanningError
from apple_compose.planner import ServicePlan


@app.command(name="port")
def port(
    ctx: typer.Context,
    service: Annotated[str, typer.Argument(help="Service to show ports for.")],
) -> None:
    """Show configured published ports for a service."""
    state: CliContext = ctx.obj
    plan = state.load_plan(services=[service], detach=True, include_dependencies=False)
    service_plan = _selected_service_plan(plan.services, service)
    if not service_plan.service.ports:
        raise PlanningError(f"Service has no published ports: {service}")

    table = Table("Service", "Port")
    for port_mapping in service_plan.service.ports:
        table.add_row(service_plan.service_name, port_mapping.to_container_arg())
    console.print(table)


def _selected_service_plan(services: list[ServicePlan], service_name: str) -> ServicePlan:
    for service in services:
        if service.service_name == service_name:
            return service
    raise PlanningError(f"Unknown service: {service_name}")
