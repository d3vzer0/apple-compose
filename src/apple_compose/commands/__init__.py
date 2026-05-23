import importlib


def register_commands() -> None:
    for module_name in (
        "apple_compose.commands.build.main",
        "apple_compose.commands.up.main",
        "apple_compose.commands.down.main",
        "apple_compose.commands.ps.main",
        "apple_compose.commands.stop.main",
        "apple_compose.commands.restart.main",
        "apple_compose.commands.logs.main",
        "apple_compose.commands.stats.main",
        "apple_compose.commands.volumes.main",
    ):
        importlib.import_module(module_name)
