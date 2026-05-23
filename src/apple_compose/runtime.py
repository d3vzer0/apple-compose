from apple_compose.container_cli import ContainerClient
from apple_compose.models import ContainerSnapshot


def load_container_snapshot(client: ContainerClient, *, project_name: str) -> ContainerSnapshot:
    running_result = client.run(["ls", "--format", "json"], capture_output=True)
    existing_result = client.run(["ls", "--all", "--format", "json"], capture_output=True)

    return ContainerSnapshot.from_command_outputs(
        running_output=running_result.stdout if running_result else None,
        existing_output=existing_result.stdout if existing_result else None,
        project_name=project_name,
    )
