class Environment:
    def __init__(
        self,
        env_config: dict,
    ) -> None:
        self.enter_steps: list = env_config["enter"] if "enter" in env_config else []
        self.exit_steps: list = env_config["exit"] if "exit" in env_config else []
        self.env_settings: dict = env_config["env_settings"] if "env_settings" in env_config else {}
        # self.execute(self.enter_steps)

    def execute(self, steps: list[dict]) -> bool:
        raise NotImplementedError

    def reset(self, reset_steps: list[dict]) -> bool:
        return self.execute(reset_steps)

    def get_env_settings(self) -> dict:
        return self.env_settings

    # def __del__(self) -> None:
    #     self.execute(self.exit_steps)
