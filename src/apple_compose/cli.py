import typer

from apple_compose.application import app
from apple_compose.commands import register_commands
from apple_compose.commands.common import console
from apple_compose.errors import AppleComposeError

register_commands()

def main() -> None:
    try:
        app()
    except AppleComposeError as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(1) from exc
