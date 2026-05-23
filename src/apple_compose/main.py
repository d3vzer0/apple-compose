from pathlib import Path
from typing import Annotated

import typer

from apple_compose.application import app
from apple_compose.commands import register_commands
from apple_compose.commands.common import CliContext, console
from apple_compose.errors import AppleComposeError, ContainerRuntimeError


@app.callback()
def callback(
    ctx: typer.Context,
    file: Annotated[
        Path,
        typer.Option(
            "--file",
            "-f",
            exists=False,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=False,
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
    """Docker Compose-like workflow for Apple Containers."""
    ctx.obj = CliContext(
        file=file,
        env_file=env_file,
        project_name=project_name,
        verbose=verbose,
        dry_run=dry_run,
    )


register_commands()


def main() -> None:
    try:
        app()
    except AppleComposeError as exc:
        if isinstance(exc, ContainerRuntimeError):
            console.print(str(exc), style="red")
        else:
            console.print(f"Error: {exc}", style="red")
        raise SystemExit(1) from None
