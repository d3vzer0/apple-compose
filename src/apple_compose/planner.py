import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from apple_compose.env import merged_environment, parse_env_file, service_env, service_env_file_paths
from apple_compose.errors import PlanningError
from apple_compose.labels import compose_labels
from apple_compose.models import BuildConfig, ComposeConfig, ServiceConfig
from apple_compose.volumes import volume_mount

CONTAINER_ARG_ATTRIBUTE = "__container_arg__"
ContainerArgRenderer = Callable[["ServicePlan"], list[str]]
BoundContainerArgRenderer = Callable[[], list[str]]


def container_arg(func: ContainerArgRenderer) -> ContainerArgRenderer:
    setattr(func, CONTAINER_ARG_ATTRIBUTE, True)
    return func


@dataclass
class ServicePlan:
    service_name: str
    service: ServiceConfig
    container_name: str
    image: str
    labels: dict[str, str]
    env_files: list[Path]
    environment: dict[str, str]
    mounts: list[str]
    network_names: list[str]
    detach: bool
    build_args: list[str] | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def run_args(self) -> list[str]:
        args: list[str] = []
        for renderer in self._container_arg_renderers():
            args.extend(renderer())
        args.extend(self._image_and_command_args())
        return args

    def _container_arg_renderers(self) -> list[BoundContainerArgRenderer]:
        return [
            getattr(self, name)
            for name, value in type(self).__dict__.items()
            if getattr(value, CONTAINER_ARG_ATTRIBUTE, False)
        ]

    @container_arg
    def _detach_args(self) -> list[str]:
        if not self.detach:
            return []
        return ["-d"]

    @container_arg
    def _name_args(self) -> list[str]:
        return ["--name", self.container_name]

    @container_arg
    def _label_args(self) -> list[str]:
        args: list[str] = []
        for key in sorted(self.labels):
            args.extend(["--label", f"{key}={self.labels[key]}"])
        return args

    @container_arg
    def _env_file_args(self) -> list[str]:
        args: list[str] = []
        for env_file in self.env_files:
            args.extend(["--env-file", str(env_file)])
        return args

    @container_arg
    def _environment_args(self) -> list[str]:
        args: list[str] = []
        for key in sorted(self.environment):
            args.extend(["--env", f"{key}={self.environment[key]}"])
        return args

    @container_arg
    def _port_args(self) -> list[str]:
        args: list[str] = []
        for port in self.service.ports:
            args.extend(["-p", port.to_container_arg()])
        return args

    @container_arg
    def _volume_args(self) -> list[str]:
        args: list[str] = []
        for mount in self.mounts:
            args.extend(["-v", mount])
        return args

    @container_arg
    def _network_args(self) -> list[str]:
        args: list[str] = []
        for network_name in self.network_names:
            args.extend(["--network", network_name])
        return args

    @container_arg
    def _hostname_args(self) -> list[str]:
        if self.service.hostname:
            return ["--hostname", self.service.hostname]
        return []

    @container_arg
    def _working_dir_args(self) -> list[str]:
        if self.service.working_dir:
            return ["--workdir", self.service.working_dir]
        return []

    @container_arg
    def _user_args(self) -> list[str]:
        if self.service.user:
            return ["--user", self.service.user]
        return []

    @container_arg
    def _platform_args(self) -> list[str]:
        if self.service.platform:
            return ["--platform", self.service.platform]
        return []

    @container_arg
    def _terminal_args(self) -> list[str]:
        args: list[str] = []
        if self.service.stdin_open:
            args.append("--interactive")
        if self.service.tty:
            args.append("--tty")
        return args

    @container_arg
    def _security_args(self) -> list[str]:
        args: list[str] = []
        if self.service.privileged:
            args.append("--privileged")
        if self.service.read_only:
            args.append("--read-only")
        return args

    @container_arg
    def _resource_args(self) -> list[str]:
        if not (
            self.service.deploy
            and self.service.deploy.resources
            and self.service.deploy.resources.limits
        ):
            return []

        args: list[str] = []
        limits = self.service.deploy.resources.limits
        if limits.cpus is not None:
            args.extend(["--cpus", str(limits.cpus)])
        if limits.memory:
            args.extend(["--memory", limits.memory])
        return args

    @container_arg
    def _entrypoint_args(self) -> list[str]:
        if self.service.entrypoint:
            entrypoint = (
                self.service.entrypoint
                if isinstance(self.service.entrypoint, str)
                else " ".join(self.service.entrypoint)
            )
            return ["--entrypoint", entrypoint]
        return []

    def _image_and_command_args(self) -> list[str]:
        args: list[str] = []
        args.extend(["--", self.image])

        if self.service.command:
            if isinstance(self.service.command, str):
                args.append(self.service.command)
            else:
                args.extend(self.service.command)
        return args


@dataclass
class AppPlan:
    project_name: str
    services: list[ServicePlan]
    network_names: list[str]
    warnings: list[str] = field(default_factory=list)


@dataclass
class Planner:
    compose: ComposeConfig
    compose_path: Path
    cwd: Path
    project_name: str | None = None
    requested_services: list[str] = field(default_factory=list)
    env_file: Path | None = None
    env_file_required: bool = False
    detach: bool = True
    include_builds: bool = False
    no_cache: bool = False

    def create_plan(self) -> AppPlan:
        resolved_project_name = resolve_project_name(self.compose, self.cwd, self.project_name)
        compose_dir = self.compose_path.parent
        project_env = (
            parse_env_file(self.env_file, required=self.env_file_required) if self.env_file else {}
        )
        base_environment = merged_environment(project_env)

        ordered_names = dependency_order(
            self.compose,
            select_services(self.compose, self.requested_services),
        )
        services = [
            self._service_plan(
                name,
                self.compose.services[name],
                compose_dir=compose_dir,
                project_name=resolved_project_name,
                base_environment=base_environment,
            )
            for name in ordered_names
        ]
        return AppPlan(
            project_name=resolved_project_name,
            services=services,
            network_names=self.compose.creatable_network_names(resolved_project_name),
        )

    def _service_plan(
        self,
        service_name: str,
        service: ServiceConfig,
        *,
        compose_dir: Path,
        project_name: str,
        base_environment: dict[str, str],
    ) -> ServicePlan:
        image = service.image or f"{service_name}:latest"
        container_name = service.container_name or f"{project_name}-{service_name}"
        mounts: list[str] = []
        for volume in service.volumes:
            mount = volume_mount(
                volume,
                compose=self.compose,
                compose_dir=compose_dir,
                project_name=project_name,
            )
            if mount:
                mounts.append(mount)

        build_args = None
        if service.build and (self.include_builds or not service.image):
            build_args = _build_args(
                service_name,
                image,
                service.build,
                compose_dir,
                no_cache=self.no_cache,
            )

        return ServicePlan(
            service_name=service_name,
            service=service,
            container_name=container_name,
            image=image,
            labels=compose_labels(project_name, service_name),
            env_files=service_env_file_paths(service.env_file, base_dir=compose_dir),
            environment=service_env(
                service.environment,
                None,
                base_dir=compose_dir,
                base_environment=base_environment,
            ),
            mounts=mounts,
            network_names=self.compose.service_network_names(service, project_name),
            detach=self.detach,
            build_args=build_args,
        )


def resolve_project_name(compose: ComposeConfig, cwd: Path, override: str | None = None) -> str:
    raw = override or compose.name or cwd.name
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")
    if not value:
        raise PlanningError("Project name resolves to an empty value")
    if value.startswith("."):
        value = f"_{value[1:]}"
    return value.lower()


def select_services(compose: ComposeConfig, requested: list[str]) -> list[str]:
    if not requested:
        return list(compose.services)

    selected: set[str] = set()

    def visit(name: str) -> None:
        if name not in compose.services:
            raise PlanningError(f"Unknown service: {name}")
        if name in selected:
            return
        for dependency in compose.services[name].depends_on:
            visit(dependency)
        selected.add(name)

    for service_name in requested:
        visit(service_name)
    return [name for name in compose.services if name in selected]


def dependency_order(compose: ComposeConfig, service_names: list[str]) -> list[str]:
    selected = set(service_names)
    permanent: set[str] = set()
    ordered: list[str] = []

    def visit(name: str) -> None:
        if name not in compose.services:
            raise PlanningError(f"Unknown service: {name}")
        if name in permanent:
            return
        for dependency in compose.services[name].depends_on:
            if dependency in selected:
                visit(dependency)
        permanent.add(name)
        ordered.append(name)

    for service_name in service_names:
        visit(service_name)
    return ordered


def create_plan(
    compose: ComposeConfig,
    *,
    compose_path: Path,
    cwd: Path,
    project_name: str | None,
    requested_services: list[str] | None = None,
    env_file: Path | None = None,
    env_file_required: bool = False,
    detach: bool = True,
    include_builds: bool = False,
    no_cache: bool = False,
) -> AppPlan:
    return Planner(
        compose=compose,
        compose_path=compose_path,
        cwd=cwd,
        project_name=project_name,
        requested_services=requested_services or [],
        env_file=env_file,
        env_file_required=env_file_required,
        detach=detach,
        include_builds=include_builds,
        no_cache=no_cache,
    ).create_plan()


def _build_args(
    service_name: str,
    image: str,
    build: BuildConfig | None,
    compose_dir: Path,
    *,
    no_cache: bool,
) -> list[str]:
    if build is None:
        raise PlanningError(f"Service {service_name} does not define build")
    context = Path(build.context).expanduser()
    if not context.is_absolute():
        context = compose_dir / context
    context = context.resolve()

    args: list[str] = []
    if no_cache:
        args.append("--no-cache")
    args.extend(["--tag", image])
    if build.dockerfile:
        dockerfile = Path(build.dockerfile)
        if not dockerfile.is_absolute():
            dockerfile = context / dockerfile
        args.extend(["--file", str(dockerfile.resolve())])

    if isinstance(build.args, dict):
        for key, value in build.args.items():
            args.extend(["--build-arg", f"{key}={value}"])
    elif isinstance(build.args, list):
        for item in build.args:
            args.extend(["--build-arg", item])

    args.append(str(context))
    return args
