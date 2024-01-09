class Environment:
    def __init__(self, app_settings: dict, steps: list[dict]) -> None:
        self.steps = steps
        self.app_settings = app_settings
        self.env_info = {}

    def reset(self) -> bool:
        raise NotImplementedError

    def get_env_info(self) -> dict:
        return self.env_info
