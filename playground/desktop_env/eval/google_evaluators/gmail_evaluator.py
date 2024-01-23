import logging
from typing import Any

from playground.config import Config
from playground.desktop_env.eval.connectors.gspace.gmail import GmailService
from playground.desktop_env.eval.evaluator import Evaluator

config = Config()
logger = logging.getLogger(__name__)


class GmailEvaluator(Evaluator):
    name: str = "gmail"

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
        self.service = GmailService()
        self.created_draft_id: str = ""
        self.retrieved_draft: dict[str, Any] | None = None

    @staticmethod
    def email_exact_match(ref: dict[str, Any], pred: dict[str, Any]) -> float:
        subject_match = ref["subject"] == pred["subject"]
        recipient_match = ref["recipient"] == pred["recipient"]
        content_match = ref["body"].strip() == pred["body"].strip()
        return float(subject_match and recipient_match and content_match)

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        try:
            for step in steps:
                for action, params in step.items():
                    match action:
                        case "create_draft":
                            draft = self.service.create_draft(
                                subject=params["subject"],
                                recipient=params["recipient"],
                                content=params["content"],
                            )
                            self.created_draft_id = draft["id"]
                        case "get_recent_draft":
                            self.retrieved_draft = self.service.get_recent_draft()
                        case "deduplicate_draft":
                            self.retrieved_draft = self.service.get_recent_draft()
                            if (
                                self.retrieved_draft is not None
                                and self.email_exact_match(self.retrieved_draft, params)
                            ):
                                self.service.delete_draft(
                                    draft_id=self.retrieved_draft["id"]
                                )
                        case _:
                            raise Exception(f"Action {action} not supported by Gmail")
            return True
        except Exception as e:
            logger.error(f"An error occurred in Gmail env: {e}")
            return False

    def __call__(self, response: str | None = None) -> float:
        score = 1.0

        try:
            for approach, value in self.reference_answer.items():
                match approach:
                    case "email_exact_match":
                        retrieved_draft: dict[
                            str, str
                        ] | None = self.service.get_recent_draft()
                        if retrieved_draft is None:
                            score = 0.0
                        else:
                            score = self.email_exact_match(value, retrieved_draft)
                    case _:
                        raise Exception(f"Method {approach} not found")
        except Exception as e:
            logger.error(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
