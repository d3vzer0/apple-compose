from importlib.metadata import PackageNotFoundError, version as package_version

from apple_compose.application import app
from apple_compose.commands.common import console


@app.command(name="version")
def version() -> None:
    """Show the apple-compose version."""
    try:
        value = package_version("apple-compose")
    except PackageNotFoundError:
        value = "unknown"
    console.print(f"apple-compose {value}")
