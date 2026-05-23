from typing import Any

from pydantic import BaseModel, ConfigDict


class ResourceLimits(BaseModel):
    model_config = ConfigDict(extra="allow")

    cpus: str | int | float | None = None
    memory: str | None = None


class DeployResources(BaseModel):
    model_config = ConfigDict(extra="allow")

    limits: ResourceLimits | None = None


class DeployConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    resources: DeployResources | None = None
    replicas: int | None = None
    restart_policy: Any = None
    update_config: Any = None
