from typing import Any

from desktop_env.eval.connectors.gspace.gmail import GmailService
from desktop_env.eval.evaluator import Evaluator


class GmailEvaluator(Evaluator):
    name: str = "gmail"

    def __init__(
        self,
        reference_answer: dict,
        reset_actions: list[dict],
        env_config: dict,
        reference_action_sequence: dict,
        eval_tag: str = "",
    ) -> None:
        super().__init__(
            reference_answer=reference_answer,
            reset_actions=reset_actions,
            env_config=env_config,
            reference_action_sequence=reference_action_sequence,
            eval_tag=eval_tag,
        )
        self.service = GmailService(
            credential_path=self.env_settings["credential_path"]
        )
        self.created_draft_id: str = ""
        self.retrieved_draft: dict[str, str] | None = None

    @staticmethod
    def email_exact_match(ref: dict, pred: dict) -> float:
        subject_match = ref["subject"] == pred["subject"]
        recipient_match = ref["recipient"] == pred["recipient"]
        content_match = ref["body"] == pred["body"].strip()
        return float(subject_match and recipient_match and content_match)

    def execute(self, steps: list[dict]) -> bool:
        try:
            for step in steps:
                action: str
                params: dict[str, Any]
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
                        case _:
                            raise Exception(f"Action {action} not supported by Gmail")
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
            print(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score

    def action2str(self, steps: list[dict]) -> list[str]:
        commands = [
            f"from desktop_env.eval.connectors.gspace.gmail import GmailService\nservice = GmailService(credential_path='{self.env_settings['credential_path']}')"  # noqa: E501
        ]
        for step in steps:
            action: str
            params: dict
            for action, params in step.items():
                match action:
                    case "create_draft":
                        commands.append(
                            f"created_draft_id = service.create_draft(subject='{params['subject']}', recipient='{params['recipient']}', content='{params['content']}')"  # noqa: E501
                        )
                    case "get_recent_draft":
                        commands.append(
                            "retrieved_draft = service.get_recent_draft()"  # noqa: E501
                        )
                    case _:
                        raise Exception(f"Action '{action}' not found")

        return commands
