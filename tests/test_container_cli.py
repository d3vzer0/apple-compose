import subprocess
from io import StringIO

import pytest
from rich.console import Console

from apple_compose.container_cli import ContainerClient
from apple_compose.errors import ContainerRuntimeError


def test_container_client_uses_runtime_stderr(monkeypatch) -> None:
    from apple_compose import container_cli

    def fail(*args, **kwargs) -> None:
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=["container", "run"],
            stderr="runtime failed\n",
        )

    monkeypatch.setattr(container_cli, "container_available", lambda: True)
    monkeypatch.setattr(container_cli.subprocess, "run", fail)

    with pytest.raises(ContainerRuntimeError) as exc_info:
        ContainerClient().run(["run"])

    assert str(exc_info.value) == "runtime failed"
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__suppress_context__


def test_container_client_redacts_env_and_build_args_in_dry_run() -> None:
    output = StringIO()
    client = ContainerClient(
        dry_run=True,
        console=Console(file=output, force_terminal=False, color_system=None),
    )

    client.run(
        [
            "run",
            "--env",
            "TOKEN=secret",
            "-e",
            "PUBLIC=value",
            "build",
            "--build-arg",
            "PASSWORD=secret",
        ]
    )

    value = output.getvalue()
    assert "TOKEN=<redacted>" in value
    assert "PUBLIC=<redacted>" in value
    assert "PASSWORD=<redacted>" in value
    assert "TOKEN=secret" not in value
    assert "PUBLIC=value" not in value
    assert "PASSWORD=secret" not in value


def test_container_client_redacts_env_in_fallback_error(monkeypatch) -> None:
    from apple_compose import container_cli

    def fail(*args, **kwargs) -> None:
        raise subprocess.CalledProcessError(returncode=1, cmd=["container", "run"])

    monkeypatch.setattr(container_cli, "container_available", lambda: True)
    monkeypatch.setattr(container_cli.subprocess, "run", fail)

    with pytest.raises(ContainerRuntimeError) as exc_info:
        ContainerClient().run(["run", "--env", "TOKEN=secret"])

    assert "TOKEN=<redacted>" in str(exc_info.value)
    assert "TOKEN=secret" not in str(exc_info.value)
