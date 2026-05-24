APPLE_COMPOSE_CREATED_BY_LABEL = "com.apple.compose.created-by"
APPLE_COMPOSE_CREATED_BY_VALUE = "apple-compose"
DOCKER_COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
DOCKER_COMPOSE_SERVICE_LABEL = "com.docker.compose.service"
DOCKER_COMPOSE_ONEOFF_LABEL = "com.docker.compose.oneoff"


def compose_labels(project_name: str, service_name: str) -> dict[str, str]:
    return {
        APPLE_COMPOSE_CREATED_BY_LABEL: APPLE_COMPOSE_CREATED_BY_VALUE,
        DOCKER_COMPOSE_PROJECT_LABEL: project_name,
        DOCKER_COMPOSE_SERVICE_LABEL: service_name,
    }
