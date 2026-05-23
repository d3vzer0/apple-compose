from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import console
from apple_compose.models import ComposeConfig
from apple_compose.planner import Planner


@app.command(name="ps")
def ps(
    file: Annotated[
        Path,
        typer.Option(
            "--file",
            "-f",
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
            help="Compose file path.",
        ),
    ] = Path("docker-compose.yml"),
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
            help="Environment file.",
        ),
    ] = None,
    project_name: Annotated[
        str | None,
        typer.Option("--project-name", "-p", help="Override the Compose project name."),
    ] = None,
) -> None:
    """Show services from the current Compose file."""
    compose = ComposeConfig.from_file(file)
    for warning in compose.warnings:
        console.print(f"Warning: {warning}", style="yellow")
    plan = Planner(
        compose=compose,
        compose_path=file,
        cwd=file.parent,
        project_name=project_name,
        requested_services=[],
        env_file=env_file if env_file else file.parent / ".env",
        env_file_required=env_file is not None,
        detach=True,
    ).create_plan()
    table = Table("Service", "Container", "Image")
    for service in plan.services:
        table.add_row(service.service_name, service.container_name, service.image)
    console.print(table)
