from desktop_env.eval.envs.environment import Environment


class FilesystemEnv(Environment):
    def __init__(self, env_configs: dict, state: dict[str, list[dict]]) -> None:
        super().__init__(env_configs, state)

    def reset(self) -> bool:
        return True

    def __del__(self) -> None:
        pass
