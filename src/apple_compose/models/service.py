from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apple_compose.models.build import BuildConfig
from apple_compose.models.deploy import DeployConfig
from apple_compose.models.port import PortMapping
from apple_compose.models.volume import VolumeMount


class ServiceConfig(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    image: str | None = None
    build: BuildConfig | None = None
    command: str | list[str] | None = None
    entrypoint: str | list[str] | None = None
    depends_on: list[str] = Field(default_factory=list)
    environment: dict[str, Any] | list[str] | None = None
    env_file: str | list[str] | None = None
    ports: list[PortMapping] = Field(default_factory=list)
    volumes: list[VolumeMount] = Field(default_factory=list)
    networks: list[str] = Field(default_factory=list)
    container_name: str | None = None
    hostname: str | None = None
    working_dir: str | None = None
    user: str | None = None
    platform: str | None = None
    stdin_open: bool = False
    tty: bool = False
    privileged: bool = False
    read_only: bool = False
    deploy: DeployConfig | None = None
    restart: Any = None
    healthcheck: Any = None
    secrets: Any = None
    configs: Any = None

    @field_validator("build", mode="before")
    @classmethod
    def normalize_build(cls, value: Any) -> Any:
        if value is None or isinstance(value, BuildConfig):
            return value
        if isinstance(value, str):
            return {"context": value}
        return value

    @field_validator("depends_on", mode="before")
    @classmethod
    def normalize_depends_on(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value)
        raise ValueError("depends_on must be a list or mapping")

    @field_validator("networks", mode="before")
    @classmethod
    def normalize_networks(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value)
        raise ValueError("networks must be a list or mapping")

    @field_validator("volumes", mode="before")
    @classmethod
    def normalize_volumes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("volumes must be a list")
        return value

    def environment_values(self, base_environment: dict[str, str]) -> dict[str, str]:
        values: dict[str, str] = {}
        if isinstance(self.environment, dict):
            for key, value in self.environment.items():
                values[str(key)] = str(value)
        elif isinstance(self.environment, list):
            for item in self.environment:
                if "=" in item:
                    key, value = item.split("=", 1)
                    values[key] = value
                elif item in base_environment:
                    values[item] = base_environment[item]
        return values

    @model_validator(mode="after")
    def must_have_image_or_build(self) -> Self:
        if not self.image and not self.build:
            raise ValueError("service must define either 'image' or 'build'")
        return self
