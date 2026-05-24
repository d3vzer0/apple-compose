from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class VolumeConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    external: bool = False


class VolumeMount(BaseModel):
    source: str
    target: str
    mode: str | None = None

    @model_validator(mode="before")
    @classmethod
    def parse_short_syntax(cls, value: Any) -> Any:
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            raise ValueError("Long volume syntax is not supported yet")
        if not isinstance(value, str):
            raise ValueError(f"Unsupported volume syntax: {value}")

        parts = value.split(":")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError(f"Unsupported volume syntax: {value}")
        if not parts[0]:
            raise ValueError("Volume source must not be empty")
        if not parts[1]:
            raise ValueError("Volume target must not be empty")

        return {
            "source": parts[0],
            "target": parts[1],
            "mode": parts[2] if len(parts) == 3 else None,
        }
