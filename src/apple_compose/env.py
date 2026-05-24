from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from dotenv.variables import parse_variables

from apple_compose.errors import InterpolationError


def parse_env_file(path: Path, *, required: bool = False) -> dict[str, str]:
    if not path.exists():
        if required:
            raise InterpolationError(f"Environment file not found: {path}")
        return {}

    values = dotenv_values(path)
    return {key: value or "" for key, value in values.items()}


def interpolate_compose_values(value: Any, environment: dict[str, str]) -> Any:
    if isinstance(value, str):
        return interpolate_string(value, environment)
    if isinstance(value, list):
        return [interpolate_compose_values(item, environment) for item in value]
    if isinstance(value, dict):
        return {
            key: interpolate_compose_values(item, environment)
            for key, item in value.items()
        }
    return value


def interpolate_string(value: str, environment: dict[str, str]) -> str:
    return "".join(atom.resolve(environment) for atom in parse_variables(value))
