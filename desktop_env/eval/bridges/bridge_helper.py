import json
from pathlib import Path

from desktop_env.eval.bridges.bridge import Environment
from desktop_env.eval.bridges.gspace.gcalendar import GoogleCalendarEnv
from desktop_env.eval.bridges.os.filesystem_env import FilesystemEnv


class EnvironmentComb:
    def __init__(self, environments: dict[str, Environment]) -> None:
        self.environments = environments

    def reset(self, reset_actions: dict[str, list]) -> bool:
        for env_name, actions in reset_actions.items():
            self.environments[env_name].reset(actions)
        return True


def environment_router(
    env_configs: dict,
) -> EnvironmentComb:
    """Router to get the environment class"""

    environments: dict[str, Environment] = {}
    for env_name, env_config in env_configs.items():
        if env_name in environments:
            raise ValueError(f"env_name {env_name} is duplicated")
        match env_name:
            case "google_calendar":
                environments[env_name] = GoogleCalendarEnv(env_config)
            case "filesystem":
                environments[env_name] = FilesystemEnv(env_config)
            case _:
                raise ValueError(f"env_name {env_name} is not supported")

    return EnvironmentComb(environments)


# TODO: this function only for testing!!!
def environment_init(
    config_file: str | Path,
) -> EnvironmentComb:
    with open(config_file, "r") as f:
        env_configs = json.load(f)

    return environment_router(env_configs)
