from pathlib import Path

from apple_compose.errors import ComposeValidationError
from apple_compose.models import ComposeConfig


def volume_mount(
    volume: str,
    *,
    compose: ComposeConfig,
    compose_dir: Path,
    project_name: str,
) -> str | None:
    parts = volume.split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise ComposeValidationError(f"Unsupported volume syntax: {volume}")

    source, target = parts[0], parts[1]
    mode = parts[2] if len(parts) == 3 else None

    is_named_volume = source in compose.volumes
    source_path = compose.resolve_volume_source(source, compose_dir, project_name)
    if is_named_volume:
        source_path.mkdir(parents=True, exist_ok=True)

    mount = f"{source_path}:{target}"
    if mode:
        mount = f"{mount}:{mode}"
    return mount
