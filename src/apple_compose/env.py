from pathlib import Path

from dotenv import dotenv_values

from apple_compose.errors import InterpolationError


def parse_env_file(path: Path, *, required: bool = False) -> dict[str, str]:
    if not path.exists():
        if required:
            raise InterpolationError(f"Environment file not found: {path}")
        return {}

    values = dotenv_values(path)
    return {key: value or "" for key, value in values.items()}
