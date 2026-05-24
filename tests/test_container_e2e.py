import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from apple_compose.container_cli import ContainerClient
from apple_compose.errors import ContainerRuntimeError
from apple_compose.main import app
from conftest import sample_text

pytestmark = pytest.mark.container_e2e

runner = CliRunner()


@pytest.fixture
def e2e_compose(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    project_name = f"apple-compose-e2e-{uuid.uuid4().hex[:12]}"
    image = os.environ.get("APPLE_COMPOSE_E2E_IMAGE", "alpine:latest")
    compose_file = tmp_path / "compose.yaml"
    compose_file.write_text(
        sample_text("compose", "e2e-basic.yaml")
        .replace("__PROJECT_NAME__", project_name)
        .replace("__IMAGE__", image)
    )

    try:
        yield compose_file, project_name
    finally:
        runner.invoke(app, ["-f", str(compose_file), "down"])
        try:
            ContainerClient().run(["rm", "--force", f"{project_name}-web"])
        except ContainerRuntimeError:
            pass


def test_container_lifecycle_subset_uses_real_container_cli(
    e2e_compose: tuple[Path, str],
) -> None:
    compose_file, project_name = e2e_compose

    assert_success(runner.invoke(app, ["-f", str(compose_file), "pull", "web"]))
    assert_success(runner.invoke(app, ["-f", str(compose_file), "up", "-d", "web"]))

    ls_result = runner.invoke(app, ["ls"])
    assert_success(ls_result)
    assert project_name in ls_result.output

    assert_success(runner.invoke(app, ["-f", str(compose_file), "stop", "web"]))
    assert_success(runner.invoke(app, ["-f", str(compose_file), "start", "web"]))
    assert_success(runner.invoke(app, ["-f", str(compose_file), "down", "web"]))

    final_ls = runner.invoke(app, ["ls"])
    assert_success(final_ls)
    assert project_name not in final_ls.output


def assert_success(result) -> None:
    details = result.output
    if result.exception is not None:
        details = f"{details}\n{result.exception}"
    assert result.exit_code == 0, details
