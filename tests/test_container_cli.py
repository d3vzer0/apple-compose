import subprocess

import pytest

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
