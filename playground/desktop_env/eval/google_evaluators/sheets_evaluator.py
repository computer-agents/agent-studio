import logging
from typing import Any

from playground.desktop_env.eval.connectors.gspace.gsheets import GoogleSheetsService
from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class GoogleSheetsEvaluator(Evaluator):
    name: str = "google_sheets"

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
        self.service = GoogleSheetsService()

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        for step in steps:
            for action, params in step.items():
                match action:
                    case "create_spreadsheet":
                        self.service.create_spreadsheet(title=params["title"])
                    case "deduplicate_spreadsheet":
                        spreadsheet_ids = self.service.search_spreadsheet_by_title(
                            params["title"]
                        )
                        if len(spreadsheet_ids) != 0:
                            self.service.deduplicate_spreadsheet(
                                spreadsheet_ids, params.get("content", None)
                            )
                    case "spreadsheet_exact_match":
                        spreadsheet_ids = self.service.get_recent_spreadsheets()
                        if len(spreadsheet_ids) != 0:
                            for spreadsheet_id in spreadsheet_ids:
                                if self.service.spreadsheet_exact_match(
                                    spreadsheet_id,
                                    params["title"],
                                    params.get("content", None),
                                ):
                                    break
                            else:
                                score = 0.0
                    case _:
                        raise Exception(
                            f"Action {action} not supported by Google Sheets"
                        )

        return score
