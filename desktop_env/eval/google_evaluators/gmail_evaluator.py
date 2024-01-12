from typing import Any, Dict

from desktop_env.eval.connectors.gspace.gmail import GmailService
from desktop_env.eval.evaluator import Evaluator


class GmailEvaluator(Evaluator):
    name: str = "gmail"

    def __init__(
        self,
        reference_answer: dict,
        reset_actions: list[dict],
        env_config: dict,
        eval_tag: str = "",
    ) -> None:
        super().__init__(reference_answer, reset_actions, env_config, eval_tag)
        self.service = GmailService(token_path=self.env_settings["token_path"])
        self.created_draft_id: str = ""
        self.retrieved_draft: Dict[str, str] | None = None

    @staticmethod
    def email_exact_match(ref: Dict, pred: Dict) -> float:
        return float(pred == ref)

    def execute(self, steps: list[dict]) -> bool:
        try:
            for step in steps:
                action: str
                params: Dict[str, Any]
                for action, params in step.items():
                    match action:
                        case "create_draft":
                            draft = self.service.create_draft(
                                params["subject"],
                                params["recipient"],
                                params["sender"],
                                params["content"],
                            )
                            self.created_draft_id = draft["id"]
                        case "get_recent_draft":
                            self.retrieved_draft = self.service.get_recent_draft()
                        case _:
                            raise Exception(
                                f"Action {action} not supported by Google calendar"
                            )
            return True
        except Exception as e:
            print(f"An error occurred in Gmail env: {e}")
            return False

    def __call__(self) -> float:
        if self.env_settings is None:
            raise ValueError(f"env_settings for {self.name} is None")
        score = 1.0

        try:
            for approach, value in self.reference_answer.items():
                match approach:
                    case "email_exact_match":
                        retrieved_draft: Dict[
                            str, str
                        ] | None = self.service.get_recent_draft()
                        if retrieved_draft is None:
                            score = 0.0
                        else:
                            score = self.email_exact_match(value, retrieved_draft)
        except Exception as e:
            print(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
