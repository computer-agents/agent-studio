import logging
from typing import Any

from playground.desktop_env.eval.connectors.gspace.gslides import GoogleSlidesService
from playground.desktop_env.eval.evaluator import Evaluator

logger = logging.getLogger(__name__)


class GoogleSlidesEvaluator(Evaluator):
    name: str = "google_slides"

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
        self.service = GoogleSlidesService()

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        try:
            for step in steps:
                for action, params in step.items():
                    match action:
                        case "create_presentation":
                            self.service.create_presentation(title=params["title"])
                        case "deduplicate_presentation":
                            presentation_ids = (
                                self.service.search_presentation_by_title(
                                    params["title"]
                                )
                            )
                            print("Pi:", presentation_ids)
                            if len(presentation_ids) != 0:
                                self.service.deduplicate_presentation(
                                    presentation_ids, params.get("content", None)
                                )
                        case "presentation_exact_match":
                            presentation_ids = self.service.get_recent_presentations()
                            if len(presentation_ids) != 0:
                                for presentation_id in presentation_ids:
                                    if self.service.presentation_exact_match(
                                        presentation_id,
                                        params["title"],
                                        params.get("content", None),
                                    ):
                                        break
                                else:
                                    score = 0.0
                        case _:
                            raise Exception(
                                f"Action {action} not supported by Google Slides"
                            )

        except Exception as e:
            logger.error(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
