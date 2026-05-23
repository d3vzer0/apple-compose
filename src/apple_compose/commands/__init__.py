import importlib


def register_commands() -> None:
    for module_name in (
        "apple_compose.commands.up.main",
        "apple_compose.commands.down.main",
        "apple_compose.commands.ps.main",
    ):
        importlib.import_module(module_name)
