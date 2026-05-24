from pydantic import BaseModel, ConfigDict


class NetworkConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    external: bool = False

    def runtime_name(self, project_name: str, key: str) -> str:
        if self.name:
            return self.name
        return f"{project_name}-{key}"
