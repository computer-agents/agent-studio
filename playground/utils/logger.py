import logging
import os
import sys
from datetime import datetime

from colorama import Fore, Style
from colorama import init as colours_on

from playground.config import Config
from playground.utils.singleton import Singleton

config = Config()
colours_on(autoreset=True)


class ColorFormatter(logging.Formatter):
    COLORS = {
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "DEBUG": Fore.GREEN,
        "INFO": Fore.WHITE,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, "")
        if color:
            record.name = color + record.name
            record.msg = record.msg + Style.RESET_ALL
        return logging.Formatter.format(self, record)


class Logger(metaclass=Singleton):
    """Singleton for logger."""

    log_file = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

    def __init__(self):
        format = "%(asctime)s\t%(levelname)s %(filename)s:%(lineno)s -- %(message)s"
        formatter = logging.Formatter(format)
        c_formatter = ColorFormatter(format)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(c_formatter)

        stderr_handler = logging.StreamHandler()
        stderr_handler.setLevel(logging.ERROR)
        stderr_handler.setFormatter(c_formatter)

        file_handler = logging.FileHandler(
            filename=os.path.join(config.log_dir, self.log_file),
            mode="w",
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logging.basicConfig(
            level=logging.DEBUG, handlers=[stdout_handler, stderr_handler, file_handler]
        )
        self.logger = logging.getLogger("Playground Logger")

    def _log(self, title="", title_color=Fore.WHITE, message="", level=logging.INFO):
        if message:
            if isinstance(message, list):
                message = " ".join(message)

        self.logger.log(level, message, extra={"title": title, "color": title_color})

    def error(
        self,
        message,
        title="",
        title_color=Fore.RED,
    ):
        self._log(title, title_color, message, logging.ERROR)

    def debug(
        self,
        message,
        title="",
        title_color=Fore.GREEN,
    ):
        self._log(title, title_color, message, logging.DEBUG)

    def info(
        self,
        message="",
        title="",
        title_color=Fore.WHITE,
    ):
        self._log(title, title_color, message, logging.INFO)

    def warn(
        self,
        message,
        title="",
        title_color=Fore.YELLOW,
    ):
        self._log(title, title_color, message, logging.WARN)
