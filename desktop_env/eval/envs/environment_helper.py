import json
from pathlib import Path
import os

from desktop_env.eval.envs.environment import Environment
from desktop_env.eval.envs.gspace.gcalendar import GoogleCalendarEnv


class EnvironmentComb:
    def __init__(self, environments: dict[str, Environment]) -> None:
        self.environments = environments

    def reset(self) -> bool:
        for _, environment in self.environments.items():
            environment.reset()
        return True


def environment_router(
    env_configs: dict,
) -> EnvironmentComb:
    """Router to get the environment class"""

    environments: dict[str, Environment] = {}
    for env_name, env_steps in env_configs["environments"].items():
        if env_name in environments:
            raise ValueError(f"env_name {env_name} is duplicated")
        match env_name:
            case "google_calendar":
                environments[env_name] = (
                    GoogleCalendarEnv(
                        env_configs["applications_settings"][env_name],
                        env_steps
                    )
                )
            case _:
                raise ValueError(f"env_name {env_name} is not supported")

    return EnvironmentComb(environments)


# TODO: this function only for testing!!!
def environment_init(
    config_file: str | Path,
) -> EnvironmentComb:
    with open(config_file, "r") as f:
        configs = json.load(f)

    with open(
        os.path.join(
            "desktop_env/eval/examples/envs", f"{configs['environment']}.json"
        ),
        "r",
    ) as f:
        env_configs = json.load(f)

    return environment_router(env_configs)
