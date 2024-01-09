class Environment:
    def __init__(self, app_settings: dict, steps: list[dict]) -> None:
        self.steps = steps
        self.app_settings = app_settings

    def reset(self) -> bool:
        raise NotImplementedError
