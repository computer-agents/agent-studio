import base64
import logging
import re
from email.message import EmailMessage
from typing import Any

from playground.config import Config
from playground.env.desktop_env.eval.connectors.gservice import GoogleService
from playground.env.desktop_env.eval.evaluator import Evaluator
from playground.utils.human_utils import confirm_action

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


def message_match(msg_to_match: dict[str, Any], ref_msg: dict[str, Any]) -> bool:
    """Checks if the msg_to_match matches the ref_msg."""
    result = True
    if "recipient" in ref_msg:
        result &= extract_email(msg_to_match["recipient"]) == extract_email(
            ref_msg["recipient"]
        )
    if "body" in ref_msg:
        result &= msg_to_match["body"].strip() == ref_msg["body"].strip()
    for key in ["subject", "attachment", "cc"]:
        if ref_msg.get(key, None) is not None:
            result &= msg_to_match[key] == ref_msg[key]

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

    def get_subject(self, message: dict[str, Any]) -> str:
        """Retrieves the subject of the message."""
        headers = message["payload"]["headers"]
        subject = next(
            header["value"] for header in headers if header["name"].lower() == "subject"
        )
        return subject

    def get_attachment_name(self, message: dict[str, Any]) -> str | None:
        """Retrieves the name of the attachment, if any."""
        if "parts" not in message["payload"]:
            return None

        for part in message["payload"]["parts"]:
            if part["filename"] != "":
                logger.error(f"filename: {part['filename']}")
                return part["filename"]

        return None

    def get_cc(self, message: dict[str, Any]) -> str | None:
        """Retrieves the cc of the message, if any."""
        headers = message["payload"]["headers"]
        try:
            cc = next(
                header["value"] for header in headers if header["name"].lower() == "cc"
            )
        except StopIteration:
            cc = None
        return cc

    def get_body(self, message: dict[str, Any]) -> str:
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

    def get_recipient(self, message: dict[str, Any]) -> str:
        """Retrieves the recipient of the message."""
        headers = message["payload"]["headers"]
        recipient = next(
            header["value"] for header in headers if header["name"].lower() == "to"
        )
        return recipient

    def get_message(self, message_id: str) -> dict[str, Any]:
        """Retrieves the full message using the message ID."""
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return {
            "subject": self.get_subject(message),
            "recipient": self.get_recipient(message),
            "body": self.get_body(message),
            "attachment": self.get_attachment_name(message),
            "cc": self.get_cc(message),
        }

    def create_draft(self, draft_info: dict[str, Any]) -> dict[str, Any]:
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

        logger.info(f'Draft message: {draft["message"]}')

        return draft

    def send_message(
        self,
        message_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Creates and sends an email message."""
        message = EmailMessage()
        message.set_content(message_info["body"])
        message["To"] = message_info.get("recipient", config.gmail_recipient)
        message["Subject"] = message_info["subject"]
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        @confirm_action
        def _send():
            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            logger.info("Message sent successfully.")
            return send_message

        logger.info(f"Sending the message {message_info}.")
        return _send()

    def search_messages(
        self, message_info: dict[str, Any], message_type: str
    ) -> list[dict[str, Any]]:
        """Searches the messages that match the given criteria."""
        # Construct the search query
        search_query = ""
        if "subject" in message_info:
            search_query += f'subject:{message_info["subject"]} '
        if "recipient" in message_info:
            search_query += f'to:{message_info["recipient"]} '
        if "cc" in message_info:
            search_query += f'cc:{message_info["cc"]} '

        match message_type:
            case "messages":
                search_result = (
                    self.service.users()
                    .messages()
                    .list(userId="me", q=search_query)
                    .execute()
                )
                messages = []
                for m in search_result.get("messages", []):
                    msg = self.get_message(m["id"])
                    msg["id"] = m["id"]
                    messages.append(msg)
            case "drafts":
                search_result = (
                    self.service.users()
                    .drafts()
                    .list(userId="me", q=search_query)
                    .execute()
                )
                messages = []
                for m in search_result.get("drafts", []):
                    msg = self.get_message(m["message"]["id"])
                    msg["id"] = m["id"]
                    messages.append(msg)
            case _:
                raise ValueError("message_type must be 'messages' or 'drafts'")

        matching_messages = []
        for msg in messages:
            if message_match(msg, message_info):
                matching_messages.append(msg)

        return matching_messages

    @confirm_action
    def delete_draft_by_id(self, draft_id: str) -> None:
        """Deletes the draft with the given ID."""
        self.service.users().drafts().delete(userId="me", id=draft_id).execute()
        logger.info("Draft deleted successfully.")

    def delete_draft(self, draft_info: dict[str, Any]) -> None:
        """Deletes the draft that matches the given criteria."""
        drafts = self.search_messages(message_info=draft_info, message_type="drafts")
        for draft in drafts:
            logger.info(f"Deleting draft with subject {draft['subject']}")
            self.delete_draft_by_id(draft["id"])

    @confirm_action
    def delete_sent_message_by_id(self, message_id: str) -> None:
        """Deletes the sent message with the given ID."""
        self.service.users().messages().delete(userId="me", id=message_id).execute()
        logger.info(f"Sent message with id {message_id} deleted successfully.")

    def delete_sent_message(self, message_info: dict[str, Any]) -> None:
        """Deletes the sent message with the given criteria."""
        sent_messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        for sent_message in sent_messages:
            logger.info(f"Deleting sent message with subject {sent_message['subject']}")
            self.delete_sent_message_by_id(sent_message["id"])

    def check_draft_exists(self, draft_info: dict[str, Any], exists: bool) -> bool:
        """Checks if the given draft exists."""
        drafts = self.search_messages(message_info=draft_info, message_type="drafts")
        draft_exists = len(drafts) > 0
        return draft_exists == exists

    def check_sent_message_exists(
        self, message_info: dict[str, Any], exists: bool
    ) -> bool:
        """Checks if the given sent message exists."""
        sent_messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        sent_message_exists = len(sent_messages) > 0
        return sent_message_exists == exists


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
            "check_sent_message_exists": self.service.check_sent_message_exists,
        }
        self.reset_handlers = {
            "create_draft": self.service.create_draft,
            "delete_draft": self.service.delete_draft,
            "delete_sent_message": self.service.delete_sent_message,
            "send_message": self.service.send_message,
        }
        self.feedback_handlers = {
            "check_draft_exists": lambda draft_info, exists: (
                f"The error occured when checking if the existence of "
                f"the draft {draft_info}. It should be {exists}."
            ),
            "check_sent_message_exists": lambda message_info, exists: (
                f"The error occured when checking if the existence of "
                f"the sent message {message_info}. It should be {exists}."
            ),
        }
