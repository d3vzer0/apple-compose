import shutil
from pathlib import Path

import pytest

from apple_compose.container_cli import container_available


TEST_DATA = Path(__file__).parent / "test_data"


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--live-tests",
        action="store_true",
        default=False,
        help="Run opt-in end-to-end tests against the real Apple container CLI.",
    )


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "container_e2e: end-to-end tests that use the real Apple container CLI",
    )


def pytest_collection_modifyitems(config, items) -> None:
    run_e2e = config.getoption("--live-tests")
    skip_reason = None
    if not run_e2e:
        skip_reason = "need --live-tests option to run"
    elif not container_available():
        skip_reason = "Apple 'container' CLI not found on PATH"

    if skip_reason is None:
        return

    skip_marker = pytest.mark.skip(reason=skip_reason)
    for item in items:
        if "container_e2e" in item.keywords:
            item.add_marker(skip_marker)


def sample_path(*parts: str) -> Path:
    return TEST_DATA.joinpath(*parts)


def sample_text(*parts: str) -> str:
    return sample_path(*parts).read_text()


def copy_sample(tmp_path: Path, *parts: str, name: str | None = None) -> Path:
    source = sample_path(*parts)
    target = tmp_path / (name or source.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target
