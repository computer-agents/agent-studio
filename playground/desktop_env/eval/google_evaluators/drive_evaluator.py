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
        # Additional properties as needed, e.g., created_file_id

    def execute(self, steps: list[dict[str, dict[str, Any]]]) -> bool:
        try:
            for step in steps:
                for action, params in step.items():
                    match action:
                        case "upload_file":
                            pass
                        case "download_file":
                            # Perform file download and verify content
                            pass
                        case "init_folder":
                            folder = self.service.create_folder(
                                folder_name=params["name"]
                            )
                            if "file_name" in params:
                                folder_id: Any = folder.get("id")
                                self.service.upload_file(
                                    file_name=params["file_name"],
                                    file_path=params["file_path"],
                                    mime_type=params["mime_type"],
                                    folder_id=folder_id,
                                )
                        case "list_files":
                            # List files and compare with expected list
                            pass
                        case "delete_file":
                            # Delete a specified file
                            pass
                        case _:
                            raise Exception(
                                f"Action {action} not supported by Google Drive"
                            )
            return True
        except Exception as e:
            logger.error(f"An error occurred in Google Drive env: {e}")
            return False

    def __call__(self) -> float:
        score = 1.0

        try:
            for approach, value in self.reference_answer.items():
                match approach:
                    case "file_match":
                        file_ids = self.service.search_file(value["name"])
                        if "content" in value:
                            score *= float(
                                self.service.compare_file_content(
                                    file_ids[0], value["content"]
                                )
                            )
                        elif len(file_ids) == 0:
                            score = 0.0
                    case "folder_exists":
                        folder_ids = self.service.search_folder(value["name"])
                        if value["answer"]:
                            score = len(folder_ids) > 0
                        else:
                            score = len(folder_ids) == 0
                    case "folder_match":
                        folder_ids = self.service.search_folder(value["name"])
                        if len(folder_ids) == 0:
                            score = 0.0
                        else:
                            files = self.service.list_files(folder_ids[0])
                            score *= float(
                                len(files) == len(value["files"])
                                and all(
                                    [
                                        ref["name"] == pred["name"]
                                        for ref, pred in zip(value["files"], files)
                                    ]
                                )
                            )
                    case _:
                        raise Exception(f"Method {approach} not found")
        except Exception as e:
            logger.error(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
