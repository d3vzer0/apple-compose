import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

from apple_compose.errors import InterpolationError


def parse_env_file(path: Path, *, required: bool = False) -> dict[str, str]:
    if not path.exists():
        if required:
            raise InterpolationError(f"Environment file not found: {path}")
        return {}

    values = dotenv_values(path)
    return {key: value or "" for key, value in values.items()}


def merged_environment(project_env: dict[str, str]) -> dict[str, str]:
    merged = dict(os.environ)
    merged.update(project_env)
    return merged


def service_env(
    environment: dict[str, Any] | list[str] | None,
    env_files: str | list[str] | None,
    *,
    base_dir: Path,
    base_environment: dict[str, str],
) -> dict[str, str]:
    merged: dict[str, str] = {}

    for env_file in _as_list(env_files):
        path = Path(env_file)
        if not path.is_absolute():
            path = base_dir / path
        file_values = parse_env_file(path, required=True)
        merged.update(file_values)

    if isinstance(environment, dict):
        for key, value in environment.items():
            merged[str(key)] = str(value)
    elif isinstance(environment, list):
        for item in environment:
            if "=" in item:
                key, value = item.split("=", 1)
                merged[key] = value
            elif item in base_environment:
                merged[item] = base_environment[item]

    return merged


def _as_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return value
