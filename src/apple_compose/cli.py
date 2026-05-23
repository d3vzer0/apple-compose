from apple_compose.application import app
from apple_compose.commands import register_commands
from apple_compose.commands.common import console
from apple_compose.errors import AppleComposeError, ContainerRuntimeError

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
