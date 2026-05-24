import importlib


def register_commands() -> None:
    for module_name in (
        "apple_compose.commands.build_.main",
        "apple_compose.commands.config.main",
        "apple_compose.commands.ls.main",
        "apple_compose.commands.up.main",
        "apple_compose.commands.down.main",
        "apple_compose.commands.ps.main",
        "apple_compose.commands.pull.main",
        "apple_compose.commands.images.main",
        "apple_compose.commands.exec.main",
        "apple_compose.commands.run.main",
        "apple_compose.commands.start.main",
        "apple_compose.commands.stop.main",
        "apple_compose.commands.restart.main",
        "apple_compose.commands.rm.main",
        "apple_compose.commands.kill.main",
        "apple_compose.commands.logs.main",
        "apple_compose.commands.port.main",
        "apple_compose.commands.stats.main",
        "apple_compose.commands.volumes.main",
        "apple_compose.commands.version.main",
    ):
        importlib.import_module(module_name)
