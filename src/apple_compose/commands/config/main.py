import typer
from rich.table import Table

from apple_compose.application import app
from apple_compose.commands.common import CliContext, console
from apple_compose.planner import resolve_project_name


@app.command(name="config")
def config(ctx: typer.Context) -> None:
    """Show a summary of the current Compose file."""
    state: CliContext = ctx.obj
    compose = state.load_compose()
    project_name = resolve_project_name(compose, state.file.parent, state.project_name)

    console.print(f"Project: {project_name}")

    services = Table("Service", "Image", "Build")
    for name, service in compose.services.items():
        build = service.build.context if service.build else ""
        services.add_row(name, service.image or "", build)
    console.print(services)

    networks = Table("Network", "Runtime Name", "External")
    for name, network in compose.networks.items():
        runtime_name = (network.runtime_name(project_name, name) if network else f"{project_name}-{name}")
        external = "yes" if network and network.external else "no"
        networks.add_row(name, runtime_name, external)
    console.print(networks)

    volumes = Table("Volume", "Runtime Name", "External")
    for name, volume in compose.volumes.items():
        runtime_name = compose.resolve_volume_source(name, state.file.parent, project_name)
        external = "yes" if volume and volume.external else "no"
        volumes.add_row(name, runtime_name, external)
    console.print(volumes)
