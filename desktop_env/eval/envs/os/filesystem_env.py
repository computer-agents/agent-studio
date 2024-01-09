from desktop_env.eval.envs.environment import Environment


class FilesystemEnv(Environment):
    def __init__(self, env_configs: dict, env_steps: list[dict]) -> None:
        super().__init__(env_configs, env_steps)

    def reset(self) -> bool:
        return True

    def __del__(self) -> None:
        pass
