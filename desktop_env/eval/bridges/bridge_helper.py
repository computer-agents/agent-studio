import json
from pathlib import Path

from desktop_env.eval.bridges.bridge import Bridge
from desktop_env.eval.bridges.gspace.gcalendar import GoogleCalendarBridge
from desktop_env.eval.bridges.os.filesystem_env import FilesystemBridge


class BridgesComb:
    def __init__(self, bridges: dict[str, Bridge]) -> None:
        self.bridges = bridges

    def reset(self, reset_actions: dict[str, list]) -> bool:
        for bridge_name, actions in reset_actions.items():
            self.bridges[bridge_name].reset(actions)
        return True


def bridge_router(
    env_configs: dict,
) -> BridgesComb:
    """Router to get the environment class"""

    bridges: dict[str, Bridge] = {}
    for bridge_name, env_config in env_configs.items():
        if bridge_name in bridges:
            raise ValueError(f"bridge_name {bridge_name} is duplicated")
        match bridge_name:
            case "google_calendar":
                bridges[bridge_name] = GoogleCalendarBridge(env_config)
            case "filesystem":
                bridges[bridge_name] = FilesystemBridge(env_config)
            case _:
                raise ValueError(f"bridge_name {bridge_name} is not supported")

    return BridgesComb(bridges)


# TODO: this function only for testing!!!
def bridge_init(
    config_file: str | Path,
) -> BridgesComb:
    with open(config_file, "r") as f:
        env_configs = json.load(f)

    return bridge_router(env_configs)
