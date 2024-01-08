from genericpath import exists
import json
from pathlib import Path
import os
import stat
from datetime import datetime
import pwd
import grp
import filecmp

from desktop_env.eval.evaluator import Evaluator


class FilesystemEvaluator(Evaluator):
    
    @staticmethod
    def evaluator_name() -> str:
        return "filesystem"

    @staticmethod
    def file_content_match(path: str, expected_content: str) -> bool:
        try:
            with open(path, 'r') as file:
                content = file.read()
            return content == expected_content
        except IOError:
            return False
    
    @staticmethod
    def file_identical(path1: str, path2: str) -> bool:
        return filecmp.cmp(path1, path2)

    @staticmethod
    def permission_match(path: str, expected_permissions: str) -> bool:
        try:
            # Convert permissions to a readable format
            st_mode = os.stat(path).st_mode
            actual_permissions = stat.filemode(st_mode)
            return actual_permissions == expected_permissions
        except IOError:
            return False

    @staticmethod
    def file_metadata_match(path: str, metadata: dict) -> bool:
        '''
        metadata is a dictionary of the form:
        {
            "last_modified": "2021-09-01T12:00:00",
            "creation_time": "2021-09-01T12:00:00",
            "size": 1000,
            "owner": "user",
            "group": "group"
        }
        '''
        def _compare_time(file_time: float, expected_iso_time: str) -> bool:
            file_datetime = datetime.fromtimestamp(file_time)
            expected_datetime = datetime.fromisoformat(expected_iso_time)
            return file_datetime == expected_datetime
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

            return True
        except IOError:
            return False

    @staticmethod
    def folder_contains_file(folder_path: str, file_name: str) -> bool:
        folder = Path(folder_path)
        return any(f.name == file_name for f in folder.iterdir() if f.is_file())
    
    @staticmethod
    def exists(path: str) -> bool:
        return Path(path).exists()

    def __call__(self, config_file: Path | str) -> float:
        with open(config_file, "r") as f:
            task_configs = json.load(f)

        with open(
                os.path.join("desktop_env/eval/examples/envs", f"{task_configs['environment']}.json")
                , "r"
            ) as f:
            env_configs = json.load(f)

        weight = task_configs["score_weight"]
        cur_score = 0.0
        total_score = 0.0
        tasks: list[dict] = task_configs["tasks"]
        
        for task in tasks:
            task_score = task["score"]
            total_score += task_score
            for eval in task["eval"]:
                if eval["eval_types"] == self.evaluator_name():
                    # TODO: the above two "for" clauses and one "if" clause 
                    # should be done by the caller, here's only an example
                    for approach, value in eval["reference_answers"].items():
                        match approach:
                            case "exists":
                                for path, exists in value.items():
                                    task_score *= float(FilesystemEvaluator.exists(path) == exists)
                            case "type_check":
                                for path, content in value.items():
                                    if content == "file":
                                        task_score *= float(Path(path).is_file())
                                    elif content == "folder":
                                        task_score *= float(Path(path).is_dir())
                            case "permissions_check":
                                for path, permissions in value.items():
                                    task_score *= float(self.permission_match(path, permissions))
                            case "content_check":
                                for path, content in value.items():
                                    task_score *= float(self.file_content_match(path, content))
                            case "metadata_check":
                                for path, metadata in value.items():
                                    task_score *= float(self.file_metadata_match(path, metadata))
            cur_score += task_score
        score = cur_score / total_score * weight

        return score
