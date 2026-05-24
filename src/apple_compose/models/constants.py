SUPPORTED_SERVICE_KEYS = {
    "image",
    "build",
    "command",
    "entrypoint",
    "depends_on",
    "environment",
    "env_file",
    "ports",
    "volumes",
    "networks",
    "container_name",
    "hostname",
    "working_dir",
    "user",
    "platform",
    "stdin_open",
    "tty",
    "privileged",
    "read_only",
    "shm_size",
    "deploy",
    "restart",
    "healthcheck",
    "secrets",
    "configs",
}

IGNORED_SERVICE_KEYS = {
    "shm_size",
    "restart",
    "healthcheck",
    "secrets",
    "configs",
}

SUPPORTED_TOP_LEVEL_KEYS = {"name", "services", "networks", "volumes"}
