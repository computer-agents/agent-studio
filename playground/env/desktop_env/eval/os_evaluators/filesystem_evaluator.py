import grp
import logging
import os
import pwd
import shutil
import stat
from datetime import datetime
from pathlib import Path

from playground.env.desktop_env.eval.evaluator import Evaluator
from playground.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)


def create_file(path: str, content: str | None = None) -> None:
    if content is not None:
        with open(path, "w") as f:
            f.write(content)
    else:
        open(path, "w").close()


def mkdir(path: str) -> None:
    dir_name = Path(path)
    dir_name.mkdir(parents=True, exist_ok=True)


def rm(path: str) -> None:
    @confirm_action
    def _rm(path: str) -> None:
        if os.path.exists(path) and os.path.isfile(path):
            os.remove(path)
        logger.info(f"{path} removed")

    logger.info(f"Removing {path}")
    _rm(path)


def rmdir(path: str) -> None:
    @confirm_action
    def _rmdir(path: str) -> None:
        if os.path.exists(path) and os.path.isdir(path):
            shutil.rmtree(path)
        logger.info(f"{path} removed")

    logger.info(f"Removing {path}")
    _rmdir(path)


def rename(old_name: str, new_name: str) -> None:
    os.rename(old_name, new_name)


def copy(src: str, dest: str) -> None:
    os.system(f"cp {src} {dest}")


def move(src: str, dest: str) -> None:
    os.system(f"mv {src} {dest}")


def chmod(path: str, mode: str) -> None:
    os.chmod(path, int(mode, 8))


def type_check(file_to_check: dict[str, str]) -> bool:
    for path, expected_type in file_to_check.items():
        if expected_type == "file":
            if not Path(path).is_file():
                return False
        elif expected_type == "folder":
            if not Path(path).is_dir():
                return False
        else:
            raise ValueError(f"Unknown type {expected_type}")
    return True


def permissions_check(file_to_check: dict[str, str]) -> bool:
    for path, expected_permissions in file_to_check.items():
        try:
            # Compare permissions as octal
            st_mode = os.stat(path).st_mode & 0o777
            if st_mode != int(expected_permissions, 8):
                return False
        except ValueError:
            # Convert permissions to a readable format
            st_mode = os.stat(path).st_mode
            actual_permissions = stat.filemode(st_mode)
            if actual_permissions != expected_permissions:
                return False
        except IOError:
            return False
    return True


def content_check(file_to_check: dict[str, str]) -> bool:
    for path, expected_content in file_to_check.items():
        try:
            with open(path, "r") as file:
                content = file.read()
            if content != expected_content:
                return False
        except IOError:
            return False
    return True


def metadata_check(file_to_check: dict[str, dict]) -> bool:
    """
    metadata is a dictionary of the form:
    {
        "last_modified": "2021-09-01T12:00:00",
        "creation_time": "2021-09-01T12:00:00",
        "size": 1000,
        "owner": "user",
        "group": "group"
    }
    """

    def _compare_time(file_time: float, expected_iso_time: str) -> bool:
        file_datetime = datetime.fromtimestamp(file_time)
        expected_datetime = datetime.fromisoformat(expected_iso_time)
        return file_datetime == expected_datetime

    for path, metadata in file_to_check.items():
        try:
            file_stat = os.stat(path)

            for key, value in metadata.items():
                if key == "last_modified":
                    if not _compare_time(file_stat.st_mtime, value):
                        return False
                elif key == "creation_time":
                    if not _compare_time(file_stat.st_ctime, value):
                        return False
                elif key == "size":
                    if file_stat.st_size != value:
                        return False
                elif key == "owner":
                    file_owner = pwd.getpwuid(file_stat.st_uid).pw_name
                    if file_owner != value:
                        return False
                elif key == "group":
                    file_group = grp.getgrgid(file_stat.st_gid).gr_name
                    if file_group != value:
                        return False

        except IOError:
            return False
    return True


def exists(file_to_check: dict[str, bool]) -> bool:
    for path, expected in file_to_check.items():
        if expected != Path(path).exists():
            return False
    return True


class FilesystemEvaluator(Evaluator):
    name: str = "filesystem"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.evaluation_handlers = {
            "exists": exists,
            "type_check": type_check,
            "permissions_check": permissions_check,
            "content_check": content_check,
            "metadata_check": metadata_check,
        }
        self.reset_handlers = {
            "create_file": create_file,
            "mkdir": mkdir,
            "rm": rm,
            "rmdir": rmdir,
            "rename": rename,
            "copy": copy,
            "move": move,
            "chmod": chmod,
        }
        self.feedback_handlers = {
            "exists": lambda file_to_check: (
                f"The error occured when checking {file_to_check}."
            ),
            "type_check": lambda file_to_check: (
                f"The error occured when checking {file_to_check}."
            ),
            "permissions_check": lambda file_to_check: (
                f"The error occured when checking {file_to_check}."
            ),
            "content_check": lambda file_to_check: (
                f"The error occured when checking {file_to_check}."
            ),
            "metadata_check": lambda file_to_check: (
                f"The error occured when checking {file_to_check}."
            ),
        }
