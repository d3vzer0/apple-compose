from pydantic import BaseModel, ConfigDict


class VolumeConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    external: bool = False
