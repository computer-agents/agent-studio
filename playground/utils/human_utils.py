from typing import Callable

import grpc

def confirm_action(func):
    def wrapper(*args, **kwargs):
        user_input = input("Confirm action (y/n): ").strip().lower()
        if user_input == "y":
            return func(*args, **kwargs)
        else:
            return False
config = Config()

def confirm_action(prompt: str) -> Callable:
    assert isinstance(prompt, str)
    def decorator(func) -> Callable:
        assert callable(func)
        def wrapper(*args, **kwargs):
            assert hasattr(config, "standalone")
            assert isinstance(config.standalone, bool)
            user_input = ""
            if config.standalone:
                user_input = input(f"{prompt}\nConfirm action (y/n): ").strip().lower()
            else:
                assert hasattr(config, "remote_server")
            if user_input == "y":

    return wrapper
