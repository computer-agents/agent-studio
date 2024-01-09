class Environment:
    def __init__(
        self,
        app_settings: dict,
        state: dict[str, list[dict]],
    ) -> None:
        enter_steps = []
        exit_steps = []
        if "enter" in state:
            enter_steps = state["enter"]
        if "exit" in state:
            exit_steps = state["exit"]
        self.enter_steps = enter_steps
        self.exit_steps = exit_steps
        self.app_settings = app_settings
        self.env_info: dict = {}

    def reset(self) -> bool:
        raise NotImplementedError

    def get_env_info(self) -> dict:
        return self.env_info
