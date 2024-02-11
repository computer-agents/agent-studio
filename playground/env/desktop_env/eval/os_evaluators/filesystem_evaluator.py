import grp
import logging
import os
import pwd
import shutil
import stat
from datetime import datetime
from pathlib import Path

from playground.env.desktop_env.eval.evaluator import Evaluator, FeedBackException
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


def type_check(file_to_check: dict[str, str]) -> None:
    for path, expected_type in file_to_check.items():
        if expected_type == "file":
            if not Path(path).is_file():
                raise FeedBackException(
                    f"The error occurd when checking {path} type. "
                    f"Expected: {expected_type}, but get: folder"
                )
        elif expected_type == "folder":
            if not Path(path).is_dir():
                raise FeedBackException(
                    f"The error occurd when checking {path} type. "
                    f"Expected: {expected_type}, but get: file"
                )
        else:
            raise ValueError(f"Unknown type {expected_type}")


def permissions_check(file_to_check: dict[str, str]) -> None:
    for path, expected_permissions in file_to_check.items():
        try:
            # Compare permissions as octal
            st_mode = os.stat(path).st_mode & 0o777
            if st_mode != int(expected_permissions, 8):
                raise FeedBackException(
                    f"The error occurd when checking {path} permissions. "
                    f"Expected: {expected_permissions}, but get: {oct(st_mode)}"
                )
        except ValueError:
            # Convert permissions to a readable format
            st_mode = os.stat(path).st_mode
            actual_permissions = stat.filemode(st_mode)
            if actual_permissions != expected_permissions:
                raise FeedBackException(
                    f"The error occurd when checking {path} permissions. "
                    f"Expected: {expected_permissions}, but get: {actual_permissions}"
                )
        except IOError:
            raise FeedBackException(
                f"The error occurd when checking {path} permissions. "
                f"Can't access path."
            )


def content_check(file_to_check: dict[str, str]) -> None:
    for path, expected_content in file_to_check.items():
        try:
            with open(path, "r") as file:
                content = file.read()
            if content != expected_content:
                raise FeedBackException(
                    f"The error occurd when checking {path} content. "
                    f"Expected: {expected_content}, but get: {content}"
                )
        except IOError:
            raise FeedBackException(
                f"The error occurd when checking {path} content. "
                f"Can't access path."
            )


def metadata_check(file_to_check: dict[str, dict]) ->  None:
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
                        raise FeedBackException(
                            f"The error occurd when checking {path} last modified time. "
                            f"Expected: {value}, but get: {file_stat.st_mtime}"
                        )
                elif key == "creation_time":
                    if not _compare_time(file_stat.st_ctime, value):
                        raise FeedBackException(
                            f"The error occurd when checking {path} creation time. "
                            f"Expected: {value}, but get: {file_stat.st_ctime}"
                        )
                elif key == "size":
                    if file_stat.st_size != value:
                        raise FeedBackException(
                            f"The error occurd when checking {path} size. "
                            f"Expected: {value}, but get: {file_stat.st_size}"
                        )
                elif key == "owner":
                    file_owner = pwd.getpwuid(file_stat.st_uid).pw_name
                    if file_owner != value:
                        raise FeedBackException(
                            f"The error occurd when checking {path} owner. "
                            f"Expected: {value}, but get: {file_owner}"
                        )
                elif key == "group":
                    file_group = grp.getgrgid(file_stat.st_gid).gr_name
                    if file_group != value:
                        raise FeedBackException(
                            f"The error occurd when checking {path} group. "
                            f"Expected: {value}, but get: {file_group}"
                        )
        except IOError:
            raise FeedBackException(
                f"The error occurd when checking {path} metadata. "
                f"Can't access path."
            )


def exists(file_to_check: dict[str, bool]) -> None:
    for path, expected in file_to_check.items():
        if expected != Path(path).exists():
            raise FeedBackException(
                f"The error occurd when checking {path} existence. "
                f"Expected: {expected}, but get: {not expected}"
            )


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
