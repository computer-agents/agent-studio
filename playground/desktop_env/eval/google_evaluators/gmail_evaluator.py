import base64
import logging
import re
from email.message import EmailMessage
from typing import Any

from playground.config import Config
from playground.desktop_env.eval.connectors.gservice import GoogleService
from playground.desktop_env.eval.evaluator import Evaluator
from playground.desktop_env.eval.google_evaluators.utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


def extract_email(s):
    """Extracts the first email address from the given string."""
    # Regex pattern to match email addresses
    email_pattern = r"[\w\.-]+@[\w\.-]+"

    # Find all matches in the string
    emails = re.findall(email_pattern, s)

    # Return the first found email or None if no email is found
    return emails[0] if emails else None


def email_match(email1: dict[str, Any], email2: dict[str, Any]) -> bool:
    """Checks if the email2 matches the email1."""
    result = email1["subject"] == email2["subject"]
    result &= extract_email(email1["recipient"]) == extract_email(email2["recipient"])
    result &= email1["body"].strip() == email2["body"].strip()

    for key in ["attachment", "cc"]:
        if key in email1:
            if key not in email2:
                key_match = False
            else:
                key_match = email1[key] == email2[key]
        else:
            key_match = True
        result &= key_match

    return result


class GmailService(GoogleService):
    def __init__(self) -> None:
        super().__init__(
            scopes=[
                "https://www.googleapis.com/auth/gmail.compose",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://mail.google.com/",
            ],
            service_name="gmail",
            service_version="v1",
        )

    def get_subject(self, message):
        """Retrieves the subject of the message."""
        headers = message["payload"]["headers"]
        subject = next(
            header["value"] for header in headers if header["name"].lower() == "subject"
        )
        return subject

    def get_attachment_name(self, message):
        """Retrieves the name of the attachment, if any."""
        if "parts" not in message["payload"]:
            return None

        for part in message["payload"]["parts"]:
            if part["filename"] != "":
                logger.error(f"filename: {part['filename']}")
                return part["filename"]

        return None

    def get_cc(self, message):
        """Retrieves the cc of the message, if any."""
        headers = message["payload"]["headers"]
        try:
            cc = next(
                header["value"] for header in headers if header["name"].lower() == "cc"
            )
        except StopIteration:
            cc = None
        logger.error(f"cc: {cc}")
        return cc

    def get_body(self, message):
        """Decodes the body of the message."""
        if message["payload"]["body"]["size"] == 0:
            # Check if there are multiple parts
            if "parts" in message["payload"]:
                for part in message["payload"]["parts"]:
                    if "parts" in part:
                        for small_part in part["parts"]:
                            if small_part["mimeType"] == "text/plain":
                                body_data = small_part["body"]["data"]
                                decoded_body = base64.urlsafe_b64decode(
                                    body_data.encode("ASCII")
                                ).decode()
                                return decoded_body
                    else:
                        if part["mimeType"] == "text/plain":
                            body_data = part["body"]["data"]
                            decoded_body = base64.urlsafe_b64decode(
                                body_data.encode("ASCII")
                            ).decode()
                            return decoded_body
            else:
                # If the body is empty, return empty string
                decoded_body = ""
        else:
            body_data = message["payload"]["body"]["data"]
            decoded_body = base64.urlsafe_b64decode(body_data.encode("ASCII")).decode()

        return decoded_body

    def get_recipient(self, message):
        """Retrieves the recipient of the message."""
        headers = message["payload"]["headers"]
        recipient = next(
            header["value"] for header in headers if header["name"].lower() == "to"
        )
        return recipient

    def get_message(self, message_id: str):
        """Retrieves the full message using the message ID."""
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return {
            "id": message["message"]["id"],
            "subject": self.get_subject(message),
            "recipient": self.get_recipient(message),
            "body": self.get_body(message),
            "attachment": self.get_attachment_name(message),
            "cc": self.get_cc(message),
        }

    def create_draft(self, draft_info: dict[str, Any]):
        """Creates a draft email message in the user's mailbox."""
        message = EmailMessage()
        message.set_content(draft_info["body"])  # "This is automated draft mail"
        message["To"] = draft_info["recipient"]  # "gduser1@workspacesamples.dev"
        message["Subject"] = draft_info["subject"]  # "Automated draft"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"message": {"raw": encoded_message}}
        draft = (
            self.service.users()
            .drafts()
            .create(userId="me", body=create_message)
            .execute()
        )

        logger.info(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')

        return draft

    def send_message(
        self,
        draft_info: dict[str, Any],
    ):
        """
        Creates and sends an email message.
            Returns: Message object, including message id
        """
        message = EmailMessage()
        message.set_content(draft_info["body"])  # "This is automated draft mail"
        message["To"] = draft_info["recipient"]  # "gduser1@workspacesamples.dev"
        if draft_info.get("sender", None) is None:
            message["From"] = (
                self.service.users().getProfile(userId="me").execute()["emailAddress"]
            )
        else:
            message["From"] = draft_info["sender"]  # "gduser2@workspacesamples.dev"
        message["Subject"] = draft_info["subject"]  # "Automated draft"

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        send_message = None

        @confirm_action
        def _send():
            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            logger.info(f'Message sent. ID: {send_message["id"]}')

        logger.info("Sending the message...")
        _send()

        return send_message

    def list_drafts(self) -> list[dict[str, Any]]:
        """Lists all drafts."""
        results = self.service.users().drafts().list(userId="me").execute()
        draft_ids = [f["id"] for f in results.get("drafts", [])]
        print("Dd:", results)
        raise Exception
        drafts = [self.get_message(draft_id) for draft_id in draft_ids]
        return drafts

    def list_sent_emails(self) -> list[dict[str, Any]]:
        """Lists all sent emails."""
        results = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["SENT"])
            .execute()
        )
        sent_email_ids = [f["id"] for f in results.get("messages", [])]
        sent_emails = [
            self.get_message(sent_email_id) for sent_email_id in sent_email_ids
        ]
        return sent_emails

    def search_drafts(self, draft_info: dict[str, Any]) -> list[dict[str, Any]]:
        """Searches for drafts that match the given criteria."""
        drafts = self.list_drafts()
        matching_drafts = []
        for draft in drafts:
            if email_match(draft, draft_info):
                matching_drafts.append(draft)
        return matching_drafts

    def search_sent_emails(
        self, sent_email_info: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Searches for sent emails that match the given criteria."""
        sent_emails = self.list_sent_emails()
        matching_sent_emails = []
        for sent_email in sent_emails:
            if email_match(sent_email, sent_email_info):
                matching_sent_emails.append(sent_email)
        return matching_sent_emails

    @confirm_action
    def delete_draft_by_id(self, draft_id: str) -> None:
        """Deletes the draft with the given ID."""
        self.service.users().drafts().delete(userId="me", id=draft_id).execute()
        logger.info(f"Draft with id {draft_id} deleted successfully.")

    def delete_draft(self, draft_info: dict[str, Any]) -> None:
        """Deletes the draft that matches the given criteria."""
        drafts = self.search_drafts(draft_info)
        for draft in drafts:
            logger.info(f"Deleting draft with subject {draft['sub ject']}")
            self.delete_draft_by_id(draft["id"])

    @confirm_action
    def delete_sent_email_by_id(self, sent_email_id: str) -> None:
        """Deletes the sent email with the given ID."""
        self.service.users().messages().delete(userId="me", id=sent_email_id).execute()
        logger.info(f"Sent email with id {sent_email_id} deleted successfully.")

    def delete_sent_email(self, sent_email_info: dict[str, Any]) -> None:
        """Deletes the sent email with the given criteria."""
        sent_emails = self.search_sent_emails(sent_email_info)
        for sent_email in sent_emails:
            logger.info(f"Deleting sent email with subject {sent_email['subject']}")
            self.delete_sent_email_by_id(sent_email["id"])

    def check_draft_exists(self, draft_info: dict[str, Any], exists: bool) -> bool:
        """Checks if the given draft exists."""
        drafts = self.search_drafts(draft_info)
        draft_exists = len(drafts) > 0
        return draft_exists == exists

    def check_sent_email_exists(
        self, sent_email_info: dict[str, Any], exists: bool
    ) -> bool:
        """Checks if the given sent email exists."""
        sent_emails = self.search_sent_emails(sent_email_info)
        sent_email_exists = len(sent_emails) > 0
        return sent_email_exists == exists


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
        self.evaluation_handlers = {
            "check_draft_exists": self.service.check_draft_exists,
            "check_sent_email_exists": self.service.check_sent_email_exists,
        }
        self.reset_handlers = {
            "create_draft": self.service.create_draft,
            "delete_draft": self.service.delete_draft,
            "delete_sent_email": self.service.delete_sent_email,
        }
