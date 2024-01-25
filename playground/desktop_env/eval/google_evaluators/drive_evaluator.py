import logging
from typing import Any

from playground.desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class GoogleDriveEvaluator(Evaluator):
    name: str = "google_drive"

    def __init__(
        self,
        reference_answer: dict,
        reset_procedure: list[dict],
        eval_tag: str = "",
    ) -> None:
        super().__init__(
            reference_answer=reference_answer,
            reset_procedure=reset_procedure,
            eval_tag=eval_tag,
        )
        self.service = GoogleDriveService()

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        for step in steps:
            for action, params in step.items():
                match action:
                    case "init_folder":
                        folder = self.service.create_folder(folder_name=params["name"])
                        if "file_name" in params:
                            folder_id: Any = folder.get("id")
                            self.service.upload_file(
                                file_name=params["file_name"],
                                file_path=params["file_path"],
                                mime_type=params["mime_type"],
                                folder_id=folder_id,
                            )
                    case "file_match":
                        file_ids = self.service.search_file_by_name(params["name"])
                        if "content" in params:
                            score *= float(
                                self.service.compare_file_content(
                                    file_ids[0], params["content"]
                                )
                            )
                        elif len(file_ids) == 0:
                            score = 0.0
                    case "file_exists":
                        file_ids = self.service.search_file_by_name(params["name"])
                        if params["exists"]:
                            score = len(file_ids) > 0
                        else:
                            score = len(file_ids) == 0
                    case "folder_exists":
                        folder_ids = self.service.search_folder(params["name"])
                        if params["exists"]:
                            score = len(folder_ids) > 0
                        else:
                            score = len(folder_ids) == 0
                    case "folder_match":
                        folder_ids = self.service.search_folder(params["name"])
                        if len(folder_ids) == 0:
                            score = 0.0
                        else:
                            files = self.service.list_files(folder_ids[0])
                            score *= float(
                                len(files) == len(params["files"])
                                and all(
                                    [
                                        ref["name"] == pred["name"]
                                        for ref, pred in zip(params["files"], files)
                                    ]
                                )
                            )
                    case _:
                        raise Exception(
                            f"Action {action} not supported by Google Drive"
                        )

        return score
