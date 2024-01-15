import json

from playground.desktop_env.computer.display.display import Display
from playground.desktop_env.computer.keyboard.keyboard import Keyboard
from playground.desktop_env.computer.mouse.mouse import Mouse
from playground.desktop_env.computer.os.os import Os


class ComputerEnv:
    def __init__(self):
        self.offline = False
        self.verbose = False

        self.mouse = Mouse(self)
        self.keyboard = Keyboard(self)
        self.display = Display(self)
        self.os = Os(self)

    # Shortcut for computer.os.languages
    @property
    def languages(self):
        return self.os.languages

    @languages.setter
    def languages(self, value):
        self.os.languages = value

    def run(self, *args, **kwargs):
        """
        Shortcut for computer.os.run
        """
        return self.os.run(*args, **kwargs)

    def exec(self, code):
        """
        Shortcut for computer.os.run("shell", code)
        """
        return self.os.run("shell", code)

    def stop(self):
        """
        Shortcut for computer.os.stop
        """
        return self.os.stop()

    def terminate(self):
        """
        Shortcut for computer.os.terminate
        """
        return self.os.terminate()

    def screenshot(self, *args, **kwargs):
        """
        Shortcut for computer.display.screenshot
        """
        return self.display.screenshot(*args, **kwargs)

    def to_dict(self):
        def json_serializable(obj):
            try:
                json.dumps(obj)
                return True
            except TypeError:
                return False

        return {k: v for k, v in self.__dict__.items() if json_serializable(v)}

    def load_dict(self, data_dict):
        for key, value in data_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
