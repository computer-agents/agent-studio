from typing import Callable

from playground.config.config import Config

config = Config()

def confirm_action(prompt: str) -> Callable:
    assert isinstance(prompt, str)
    def decorator(func) -> Callable:
        assert callable(func)
        def wrapper(*args, **kwargs):
            if config.need_human_confirmation:
                user_input = input(f"{prompt}\nConfirm action (y/n): ").strip().lower()
                if user_input == "y":
                    return True, func(*args, **kwargs)
                else:
                    return False, None
            else:
                return True, func(*args, **kwargs)

        return wrapper
    return decorator
