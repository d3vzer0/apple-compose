from pathlib import Path
from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import console
from apple_compose.container_cli import ContainerClient
from apple_compose.models import ComposeConfig
from apple_compose.planner import Planner


@app.command(name="down")
def down(
    services: Annotated[
        list[str] | None,
        typer.Argument(help="Services to stop and remove."),
    ] = None,
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
    verbose: Annotated[bool, typer.Option("--verbose", help="Print container commands.")] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print generated container commands without executing."),
    ] = False,
) -> None:
    """Stop and remove services."""
    compose = ComposeConfig.from_file(file)
    for warning in compose.warnings:
        console.print(f"Warning: {warning}", style="yellow")
    plan = Planner(
        compose=compose,
        compose_path=file,
        cwd=file.parent,
        project_name=project_name,
        requested_services=services or [],
        env_file=env_file if env_file else file.parent / ".env",
        env_file_required=env_file is not None,
        detach=True,
    ).create_plan()
    container_client = ContainerClient(dry_run=dry_run, verbose=verbose, console=console)
    for service in reversed(plan.services):
        container_client.run(["rm", "--force", service.container_name])
