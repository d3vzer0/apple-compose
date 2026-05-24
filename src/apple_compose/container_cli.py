import shlex
import shutil
import subprocess
from dataclasses import dataclass

from rich.console import Console

from apple_compose.errors import ContainerRuntimeError


def container_available() -> bool:
    return shutil.which("container") is not None


@dataclass
class ContainerClient:
    dry_run: bool = False
    verbose: bool = False
    console: Console | None = None

    def __post_init__(self) -> None:
        if self.console is None:
            self.console = Console()

    def run(
        self,
        args: list[str],
        *,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        command = ["container", *args]
        if self.dry_run:
            self.console.print(_format_redacted_command(command))
            return None
        if not container_available():
            raise ContainerRuntimeError("Apple 'container' CLI was not found on PATH")
        if self.verbose:
            self.console.print("+ " + _format_redacted_command(command))
        try:
            return subprocess.run(
                command,
                shell=False,
                check=True,
                text=True,
                capture_output=capture_output,
            )
        except subprocess.CalledProcessError as exc:
            message = _command_error_message(exc, command)
            raise ContainerRuntimeError(message) from None


def _command_error_message(
    exc: subprocess.CalledProcessError,
    command: list[str],
) -> str:
    for output in (exc.stderr, exc.stdout):
        if output:
            message = output.strip()
            if message:
                return message
    return f"container command failed: {_format_redacted_command(command)}"


def _format_redacted_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in _redacted_command(command))


def _redacted_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for part in command:
        if redact_next:
            redacted.append(_redact_assignment(part))
            redact_next = False
            continue

        redacted.append(part)
        if part in {"--env", "-e", "--build-arg"}:
            redact_next = True
    return redacted


def _redact_assignment(value: str) -> str:
    if "=" not in value:
        return value
    key, _ = value.split("=", 1)
    return f"{key}=<redacted>"
