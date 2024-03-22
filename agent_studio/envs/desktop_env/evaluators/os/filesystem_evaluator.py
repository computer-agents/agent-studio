import configparser
import filecmp
import logging
import os
import platform
import shutil
import stat
from datetime import datetime
from pathlib import Path

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.utils.human_utils import confirm_action

# TODO: support for Windows

logger = logging.getLogger(__name__)


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

    @staticmethod
    @evaluation_handler("exists")
    def exists(file_to_check: dict[str, bool]) -> None:
        for path, expected in file_to_check.items():
            path = os.path.expanduser(path)
            if expected != Path(path).exists():
                raise FeedbackException(
                    f"The error occurred when checking {path} existence. "
                    f"Expected: {expected}, but get: {not expected}"
                )

    @staticmethod
    @evaluation_handler("type_check")
    def type_check(file_to_check: dict[str, str]) -> None:
        for path, expected_type in file_to_check.items():
            path = os.path.expanduser(path)
            if expected_type == "file":
                if not Path(path).is_file():
                    raise FeedbackException(
                        f"The error occurred when checking {path} type. "
                        f"Expected: {expected_type}, but get: folder"
                    )
            elif expected_type == "folder":
                if not Path(path).is_dir():
                    raise FeedbackException(
                        f"The error occurred when checking {path} type. "
                        f"Expected: {expected_type}, but get: file"
                    )
            else:
                raise ValueError(f"Unknown type {expected_type}")

    @staticmethod
    @evaluation_handler("permissions_check")
    def permissions_check(file_to_check: dict[str, str]) -> None:
        if platform.system() != "Windows":
            for path, expected_permissions in file_to_check.items():
                path = os.path.expanduser(path)
                try:
                    # Compare permissions as octal
                    st_mode = os.stat(path).st_mode & 0o777
                    if st_mode != int(expected_permissions, 8):
                        raise FeedbackException(
                            f"The error occurred when checking {path} permissions. "
                            f"Expected: {expected_permissions}, but get: {oct(st_mode)}"
                        )
                except ValueError:
                    # Convert permissions to a readable format
                    st_mode = os.stat(path).st_mode
                    actual_permissions = stat.filemode(st_mode)
                    if actual_permissions != expected_permissions:
                        raise FeedbackException(
                            f"The error occurred when checking {path} permissions. "
                            f"Expected: {expected_permissions}, "
                            f"but get: {actual_permissions}"
                        )
                except IOError:
                    raise FeedbackException(
                        f"The error occurred when checking {path} permissions. "
                        f"Can't access path."
                    )
        else:
            logger.warning("Permissions check is not supported on this platform.")

    @staticmethod
    @evaluation_handler("content_check")
    def content_check(file_to_check: dict[str, str], method: str = "exact") -> None:
        for path, expected_content in file_to_check.items():
            path = os.path.expanduser(path)
            try:
                with open(path, "r") as file:
                    content = file.read()
                if method == "exact":
                    if content != expected_content:
                        raise FeedbackException(
                            f"The error occurred when checking {path} content. "
                            f"Expected: {expected_content}, but get: {content}"
                        )
                elif method == "strip":
                    if content.strip() != expected_content.strip():
                        raise FeedbackException(
                            f"The error occurred when checking {path} content. "
                            f"Expected: {expected_content}, but get: {content}"
                        )
                else:
                    raise ValueError(f"Unknown content_check method: {method}")
            except IOError:
                raise FeedbackException(
                    f"The error occurred when checking {path} content. "
                    f"Can't access path."
                )

    @staticmethod
    @evaluation_handler("metadata_check")
    def metadata_check(file_to_check: dict[str, dict]) -> None:
        """
        Check file metadata.

        Args:
            file_to_check: dict[str, dict]:
                Dictionary with file path as key and metadata as value.
                Metadata is a dictionary with keys:
                last_modified, creation_time, size, owner, group.
                last_modified and creation_time are in ISO format.
                size is in bytes.
                owner and group are strings.

        Raises:
            FeedbackException: If metadata doesn't match expected values.

        Example::

            file_to_check = {
                "tmp/test.txt": {
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
                path = os.path.expanduser(path)
                file_stat = os.stat(path)

                for key, value in metadata.items():
                    if key == "last_modified":
                        if not _compare_time(file_stat.st_mtime, value):
                            raise FeedbackException(
                                f"The error occurred "
                                f"when checking {path} last modified time. "
                                f"Expected: {value}, but get: {file_stat.st_mtime}"
                            )
                    elif key == "creation_time":
                        if not _compare_time(file_stat.st_ctime, value):
                            raise FeedbackException(
                                f"The error occurred "
                                f"when checking {path} creation time. "
                                f"Expected: {value}, but get: {file_stat.st_ctime}"
                            )
                    elif key == "size":
                        if file_stat.st_size != value:
                            raise FeedbackException(
                                f"The error occurred when checking {path} size. "
                                f"Expected: {value}, but get: {file_stat.st_size}"
                            )
                    elif key == "owner":
                        if platform.system() != "Windows":
                            import pwd

                            file_owner = pwd.getpwuid(file_stat.st_uid).pw_name
                            if file_owner != value:
                                raise FeedbackException(
                                    f"The error occurred when checking {path} owner. "
                                    f"Expected: {value}, but get: {file_owner}"
                                )
                        else:
                            logger.warning(
                                "Owner check is not supported on this platform."
                            )
                    elif key == "group":
                        if platform.system() != "Windows":
                            import grp

                            file_group = grp.getgrgid(file_stat.st_gid).gr_name
                            if file_group != value:
                                raise FeedbackException(
                                    f"The error occurred when checking {path} group. "
                                    f"Expected: {value}, but get: {file_group}"
                                )
                        else:
                            logger.warning(
                                "Group check is not supported on this platform."
                            )

            except IOError:
                raise FeedbackException(
                    f"The error occurred when checking {path} metadata. "
                    f"Can't access path."
                )

    @staticmethod
    @evaluation_handler("verify_ini")
    def verify_ini(target_path: str, ref_path: str) -> None:
        """
        Compare two ini files.

        Args:
            target_path: str: Path to the target ini file.
            ref_path: str: Path to the reference ini file.

        Raises:
            FeedbackException: If the files don't match.
        """

        def _read_ini_file(file_path: str) -> dict:
            config = configparser.ConfigParser()
            config.read(file_path)
            ini_dict = {
                section: dict(config.items(section)) for section in config.sections()
            }
            return ini_dict

        ref_path = os.path.expanduser(ref_path)
        target_path = os.path.expanduser(target_path)

        if not os.path.exists(ref_path):
            raise ValueError(f"Reference file {ref_path} does not exist.")
        if not os.path.exists(target_path):
            raise FeedbackException(f"Target file {target_path} does not exist.")
        target_ini = _read_ini_file(target_path)
        ref_ini = _read_ini_file(ref_path)
        if target_ini != ref_ini:
            raise FeedbackException(
                f"Expect content:\n{ref_ini}\n" f"But get: {target_ini}"
            )

    @staticmethod
    @evaluation_handler("match_file")
    def match_file(file_to_check: dict[str, str]) -> None:
        for path, expected_path in file_to_check.items():
            path = os.path.expanduser(path)
            expected_path = os.path.expanduser(expected_path)
            if not filecmp.cmp(path, expected_path, shallow=False):
                raise FeedbackException(
                    f"The error occurred when checking {path}."
                    f"Expected: {expected_path}"
                )

    @staticmethod
    @reset_handler("create_file")
    def create_file(path: str, content: str | None = None) -> None:
        path = os.path.expanduser(path)
        if content is not None:
            with open(path, "w") as f:
                f.write(content)
        else:
            open(path, "w").close()

    @reset_handler("create_directory")
    def create_directory(self, path: str):
        path = os.path.expanduser(path)
        os.makedirs(path, exist_ok=True)

    @staticmethod
    @reset_handler("mkdir")
    def mkdir(path: str) -> None:
        path = os.path.expanduser(path)
        dir_name = Path(path)
        dir_name.mkdir(parents=True, exist_ok=True)

    @staticmethod
    @reset_handler("rm")
    def rm(path: str) -> None:
        @confirm_action(f"Removing {path}")
        def _rm(path: str) -> None:
            if os.path.exists(path) and os.path.isfile(path):
                os.remove(path)
            logger.debug(f"{path} removed")

        path = os.path.expanduser(path)
        logger.debug(f"Removing {path}")
        _rm(path)

    @staticmethod
    @reset_handler("rmdir")
    def rmdir(path: str) -> None:
        @confirm_action(f"Removing {path}")
        def _rmdir(path: str) -> None:
            if os.path.exists(path) and os.path.isdir(path):
                shutil.rmtree(path)
            logger.debug(f"{path} removed")

        path = os.path.expanduser(path)
        logger.debug(f"Removing {path}")
        _rmdir(path)

    @staticmethod
    @reset_handler("rename")
    def rename(old_name: str, new_name: str) -> None:
        old_name = os.path.expanduser(old_name)
        new_name = os.path.expanduser(new_name)
        os.rename(old_name, new_name)

    @staticmethod
    @reset_handler("copy")
    def copy(src: str, dest: str) -> None:
        src = os.path.expanduser(src)
        dest = os.path.expanduser(dest)
        os.system(f"cp {src} {dest}")

    @staticmethod
    @reset_handler("move")
    def move(src: str, dest: str) -> None:
        src = os.path.expanduser(src)
        dest = os.path.expanduser(dest)
        os.system(f"mv {src} {dest}")

    @staticmethod
    @reset_handler("chmod")
    def chmod(path: str, mode: str) -> None:
        path = os.path.expanduser(path)
        if platform.system() != "Windows":
            os.chmod(path, int(mode, 8))
        else:
            logger.warning("Chmod is not supported on this platform.")
