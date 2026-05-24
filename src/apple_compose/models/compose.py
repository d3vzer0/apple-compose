import os
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field, model_validator

from apple_compose.env import interpolate_compose_values, parse_env_file
from apple_compose.errors import ComposeValidationError
from apple_compose.models.constants import (
    IGNORED_SERVICE_KEYS,
    SUPPORTED_SERVICE_KEYS,
    SUPPORTED_TOP_LEVEL_KEYS,
)
from apple_compose.models.network import NetworkConfig
from apple_compose.models.service import ServiceConfig
from apple_compose.models.volume import VolumeConfig
from apple_compose.models.yaml_loader import MAX_COMPOSE_FILE_BYTES, UniqueKeyLoader


class ComposeConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    services: dict[str, ServiceConfig]
    networks: dict[str, NetworkConfig | None] = Field(default_factory=dict)
    volumes: dict[str, VolumeConfig | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dependency_graph(self) -> Self:
        for service_name, service in self.services.items():
            for dependency in service.depends_on:
                if dependency not in self.services:
                    raise ValueError(
                        f"Service {service_name} depends on unknown service: {dependency}"
                    )

        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(name: str) -> None:
            if name in permanent:
                return
            if name in temporary:
                raise ValueError(f"Dependency cycle detected at service: {name}")
            temporary.add(name)
            for dependency in self.services[name].depends_on:
                visit(dependency)
            temporary.remove(name)
            permanent.add(name)

        for service_name in self.services:
            visit(service_name)
        return self

    @classmethod
    def from_file(
        cls,
        file_path: Path,
        *,
        env_file: Path | None = None,
        env_file_required: bool = False,
    ) -> Self:
        if file_path.stat().st_size > MAX_COMPOSE_FILE_BYTES:
            raise ComposeValidationError(
                f"Compose file is too large: {file_path} exceeds {MAX_COMPOSE_FILE_BYTES} bytes"
            )

        try:
            raw = yaml.load(file_path.read_text(), Loader=UniqueKeyLoader)
        except ComposeValidationError:
            raise
        except yaml.YAMLError as exc:
            raise ComposeValidationError(f"Invalid YAML in {file_path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise ComposeValidationError("Compose file must be a mapping at the top level")

        project_env = (
            parse_env_file(env_file, required=env_file_required) if env_file else {}
        )
        environment = dict(os.environ)
        environment.update(project_env)
        raw = interpolate_compose_values(raw, environment)
        try:
            return cls.model_validate(raw)
        except ValidationError as exc:
            raise ComposeValidationError(str(exc)) from exc

    def creatable_network_names(self, project_name: str) -> list[str]:
        names: list[str] = []
        for key, config in self.networks.items():
            network = config or NetworkConfig()
            if network.external:
                continue
            names.append(network.runtime_name(project_name, key))
        if self.uses_implicit_default_network() and "default" not in self.networks:
            names.append(NetworkConfig().runtime_name(project_name, "default"))
        return names

    def service_network_names(self, service: ServiceConfig, project_name: str) -> list[str]:
        names: list[str] = []
        for key in service.networks or ["default"]:
            network = self.networks.get(key) or NetworkConfig()
            names.append(network.runtime_name(project_name, key))
        return names

    def uses_implicit_default_network(self) -> bool:
        return any(not service.networks for service in self.services.values())

    def resolve_volume_source(self, source: str, compose_dir: Path, project_name: str) -> str:
        if source in self.volumes:
            volume_config = self.volumes.get(source)
            if volume_config and volume_config.name:
                return volume_config.name
            if volume_config and volume_config.external:
                return source
            return f"{project_name}-{source}"

        path = Path(source).expanduser()
        if not path.is_absolute():
            path = compose_dir / path
        return str(path.resolve())

    @computed_field
    @property
    def warnings(self) -> list[str]:
        warnings: list[str] = []
        for key in self.model_extra or {}:
            if key not in SUPPORTED_TOP_LEVEL_KEYS:
                warnings.append(f"Ignoring unsupported top-level key: {key}")

        for service_name, service in self.services.items():
            for key in service.model_extra or {}:
                if key not in SUPPORTED_SERVICE_KEYS:
                    warnings.append(f"Ignoring unsupported key on service {service_name}: {key}")

            for key in IGNORED_SERVICE_KEYS:
                if getattr(service, key) is not None:
                    warnings.append(f"Parsed but not implemented for service {service_name}: {key}")

            if service.deploy:
                for key in ("replicas", "restart_policy", "update_config"):
                    if getattr(service.deploy, key) is not None:
                        warnings.append(
                            f"Parsed but not implemented for service {service_name}: deploy.{key}"
                        )
        return warnings
