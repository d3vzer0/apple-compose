from pathlib import Path
from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands.common import console
from apple_compose.container_cli import ContainerClient
from apple_compose.models import ComposeConfig
from apple_compose.planner import Planner


@app.command(name="up")
def up(
    services: Annotated[list[str] | None, typer.Argument(help="Services to start.")] = None,
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
    detach: Annotated[
        bool,
        typer.Option("--detach", "-d", help="Run containers detached."),
    ] = False,
    project_name: Annotated[
        str | None,
        typer.Option("--project-name", "-p", help="Override the Compose project name."),
    ] = None,
    build: Annotated[bool, typer.Option("--build", help="Build images before starting.")] = False,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="Build without cache.")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", help="Print container commands.")] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print generated container commands without executing."),
    ] = False,
) -> None:
    """Create and start services."""
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
        detach=detach,
        include_builds=build,
        no_cache=no_cache,
    ).create_plan()
    container_client = ContainerClient(dry_run=dry_run, verbose=verbose, console=console)

    for network_name in plan.network_names:
        container_client.run(["network", "create", network_name])
    for service in plan.services:
        if service.build_args:
            container_client.run(["build", *service.build_args])
    for service in plan.services:
        container_client.run(["run", *service.run_args])
