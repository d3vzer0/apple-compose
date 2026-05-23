from typing import Any

from pydantic import BaseModel, ConfigDict


class BuildConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    context: str = "."
    dockerfile: str | None = None
    args: dict[str, Any] | list[str] | None = None
