import logging
import re
from typing import Any

from playground.config import Config
from playground.desktop_env.eval.connectors.gspace.gmail import GmailService
from playground.desktop_env.eval.evaluator import Evaluator

config = Config()
logger = logging.getLogger(__name__)


def extract_email(s):
    # Regex pattern to match email addresses
    email_pattern = r"[\w\.-]+@[\w\.-]+"

    # Find all matches in the string
    emails = re.findall(email_pattern, s)

    # Return the first found email or None if no email is found
    return emails[0] if emails else None


class GmailEvaluator(Evaluator):
    name: str = "gmail"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = GmailService()
        self.created_draft_id: str = ""
        self.retrieved_draft: dict[str, Any] | None = None

    @staticmethod
    def email_exact_match(ref: dict[str, Any], pred: dict[str, Any]) -> float:
        subject_match = ref["subject"] == pred["subject"]
        recipient_match = extract_email(ref["recipient"]) == extract_email(
            pred["recipient"]
        )
        content_match = ref["body"].strip() == pred["body"].strip()

        key_matches = []
        for key in ["attachment", "cc"]:
            if key in ref:
                if key not in pred:
                    key_match = False
                else:
                    key_match = ref[key] == pred[key]
            else:
                key_match = True
            key_matches.append(key_match)

        return float(
            subject_match and recipient_match and content_match and all(key_matches)
        )

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
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
                        if self.retrieved_draft is not None and self.email_exact_match(
                            params, self.retrieved_draft
                        ):
                            self.service.delete_draft(
                                draft_id=self.retrieved_draft["id"]
                            )
                    case "delete_sent_email":
                        self.recent_sent_mail = self.service.get_recent_sent_mail()
                        params["recipient"] = config.gmail_recipient
                        if (
                            self.recent_sent_mail is not None
                            and self.email_exact_match(params, self.recent_sent_mail)
                        ):
                            self.service.delete_sent_email(
                                sent_email_id=self.recent_sent_mail["id"]
                            )
                    case "email_exact_match":
                        retrieved_draft: dict[
                            str, str
                        ] | None = self.service.get_recent_draft()
                        if retrieved_draft is None:
                            score = 0.0
                        else:
                            score = self.email_exact_match(params, retrieved_draft)
                    case "sent_email_exact_match":
                        sent_email: dict[
                            str, str
                        ] | None = self.service.get_recent_sent_mail()
                        if sent_email is None:
                            score = 0.0
                        else:
                            params["recipient"] = config.gmail_recipient
                            score = self.email_exact_match(params, sent_email)
                    case _:
                        raise Exception(f"Action {action} not supported by Gmail")

        return score
