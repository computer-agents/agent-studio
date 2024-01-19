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

    def file_match(self, ref: dict, pred: dict) -> float:
        # Implement matching logic based on file properties such as name, type, content
        # Example:
        name_match = ref["name"] == pred["name"]
        type_match = ref["mimeType"] == pred["mimeType"]
        # Add more checks as necessary
        return float(name_match and type_match)

    def execute(self, steps: list[dict[str, dict[str, Any]]]) -> bool:
        try:
            for step in steps:
                for action, params in step.items():
                    match action:
                        case "upload_file":
                            # Perform file upload
                            # Store created file ID for later use
                            pass
                        case "download_file":
                            # Perform file download and verify content
                            pass
                        case "create_folder":
                            # Create folder and store ID
                            pass
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
                        # Implement the logic to retrieve file information
                        # and compare it with the reference answer
                        # Adjust score based on the comparison result
                        pass
                    case _:
                        raise Exception(f"Method {approach} not found")
        except Exception as e:
            logger.error(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
