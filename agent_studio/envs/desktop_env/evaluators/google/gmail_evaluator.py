import base64
import logging
import re
from email.message import EmailMessage
from typing import Any

from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import (
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.envs.desktop_env.evaluators.google.evaluator_base import (
    GoogleEvaluatorBase,
)
from agent_studio.envs.desktop_env.evaluators.google.gservice import GoogleService
from agent_studio.utils.human_utils import confirm_action

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


def get_attachment_name(raw_message: dict[str, Any]) -> str | None:
    """Retrieves the name of the attachment, if any."""
    if "parts" not in raw_message["payload"]:
        return None

    for part in raw_message["payload"]["parts"]:
        if part["filename"] != "":
            logger.error(f"filename: {part['filename']}")
            return part["filename"]

    return None


def get_body(raw_message: dict[str, Any]) -> str:
    """Decodes the body of the message."""

    if raw_message["payload"]["body"]["size"] == 0:
        # Check if there are multiple parts
        if "parts" in raw_message["payload"]:
            for part in raw_message["payload"]["parts"]:
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
        body_data = raw_message["payload"]["body"]["data"]
        decoded_body = base64.urlsafe_b64decode(body_data.encode("ASCII")).decode()

    return decoded_body


def get_message_from_raw(raw_message: dict[str, Any]) -> dict[str, Any]:
    headers = raw_message["payload"]["headers"]
    subject: str = next(
        header["value"] for header in headers if header["name"].lower() == "subject"
    )
    recipient: str = next(
        header["value"] for header in headers if header["name"].lower() == "to"
    )
    cc: str | None
    try:
        cc = next(
            header["value"] for header in headers if header["name"].lower() == "cc"
        )
    except StopIteration:
        cc = None
    body: str = get_body(raw_message)
    attachment: str | None = get_attachment_name(raw_message)

    return dict(
        subject=subject,
        recipient=recipient,
        body=body,
        cc=cc,
        attachment=attachment,
    )


class GmailEvaluator(GoogleEvaluatorBase):
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
        self.service = GoogleService(
            scopes=[
                "https://www.googleapis.com/auth/gmail.compose",
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://mail.google.com/",
            ],
            service_name="gmail",
            service_version="v1",
        ).service

    @evaluation_handler("check_draft_exists")
    def check_draft_exists(
        self,
        draft_info: dict[str, Any],
        exists: bool,
    ) -> None:
        """Checks if the given draft exists."""
        drafts = self.search_messages(message_info=draft_info, message_type="drafts")
        draft_exists = len(drafts) > 0
        if draft_exists != exists:
            raise FeedbackException(
                f"The error occured when checking if the existence of "
                f"the draft {draft_info}. It should be {exists}."
            )

    @evaluation_handler("check_sent_message_exists")
    def check_sent_message_exists(
        self,
        message_info: dict[str, Any],
        exists: bool,
    ) -> None:
        """Checks if the given sent message exists."""
        sent_messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        sent_message_exists = len(sent_messages) > 0
        if sent_message_exists != exists:
            raise FeedbackException(
                f"The error occured when checking if the existence of "
                f"the sent message {message_info}. It should be {exists}."
            )

    @evaluation_handler("is_email_marked_important")
    def is_email_marked_important(
        self,
        message_info: dict[str, Any],
        gt: bool,
    ):
        """Checks if the email with the given ID is marked as important."""
        messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        for msg in messages:
            message = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["LabelIds"],
                )
                .execute()
            )
            is_important = "IMPORTANT" in message.get("labelIds", [])
            if is_important != gt:
                raise FeedbackException(
                    f"Email {msg['id']} is marked as important: {is_important}. "
                    f"It should be {gt}."
                )

    @evaluation_handler("check_label_exists")
    def check_label_exists(
        self,
        label_name: str,
        exists: bool,
    ):
        """Checks if a label exists by name."""
        labels = (
            self.service.users().labels().list(userId="me").execute().get("labels", [])
        )
        label_exists = any(
            label for label in labels if label["name"].lower() == label_name.lower()
        )
        if label_exists != exists:
            raise FeedbackException(
                f"Label {label_name} exists: {label_exists}. " f"It should be {exists}."
            )

    @evaluation_handler("email_has_label")
    def email_has_label(
        self,
        message_info: dict[str, Any],
        label_name: str,
        gt: bool,
    ):
        messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        for msg in messages:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="metadata")
                .execute()
            )
            label_ids = message.get("labelIds", [])
            all_labels = (
                self.service.users()
                .labels()
                .list(userId="me")
                .execute()
                .get("labels", [])
            )
            label_id = next(
                (
                    label["id"]
                    for label in all_labels
                    if label["name"].lower() == label_name.lower()
                ),
                None,
            )
            email_has_label = label_id in label_ids if label_id else False
            if email_has_label != gt:
                raise FeedbackException(
                    f"Email {msg['id']} has label {label_name}: {email_has_label}. "
                    f"It should be {gt}."
                )

    @reset_handler("delete_label")
    def delete_label(
        self,
        label_name: str,
    ) -> None:
        all_labels = (
            self.service.users().labels().list(userId="me").execute().get("labels", [])
        )
        label_id = next(
            (
                label["id"]
                for label in all_labels
                if label["name"].lower() == label_name.lower()
            ),
            None,
        )
        if label_id:
            self.service.users().labels().delete(userId="me", id=label_id).execute()

    @reset_handler("create_label")
    def create_label(
        self,
        label_name: str,
        label_list_visibility: str = "labelShow",
        message_list_visibility: str = "show",
    ) -> None:
        new_label = {
            "name": label_name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }
        self.service.users().labels().create(userId="me", body=new_label).execute()

    @evaluation_handler("is_email_in_trash")
    def is_email_in_trash(
        self,
        message_info: dict[str, Any],
        in_trash: bool,
    ):
        """Checks if the email with the given ID exists in trash."""
        messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        for msg in messages:
            message = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["LabelIds"],
                )
                .execute()
            )
            email_in_trash = "TRASH" in message.get("labelIds", [])
            if email_in_trash != in_trash:
                raise FeedbackException(
                    f"Email {msg['id']} is in trash: {email_in_trash}. "
                    f"It should be {in_trash}."
                )

    @reset_handler("create_draft")
    def create_draft(
        self,
        draft_info: dict[str, Any],
    ) -> None:
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

        logger.debug(msg=f'Draft message: {draft["message"]}')

    @reset_handler("delete_draft")
    def delete_draft(
        self,
        draft_info: dict[str, Any],
    ) -> None:
        """Deletes the draft that matches the given criteria."""
        drafts = self.search_messages(message_info=draft_info, message_type="drafts")
        for draft in drafts:
            logger.debug(f"Deleting draft with subject {draft['subject']}")
            confirm_action(f"Deleting draft with subject {draft['subject']}")(
                self.delete_draft_by_id
            )(draft["id"])

    @reset_handler("add_email_to_trash")
    def add_email_to_trash(
        self,
        message_info: dict[str, Any],
    ) -> None:
        """Moves an email to the trash."""
        messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        for msg in messages:
            self.service.users().messages().trash(userId="me", id=msg["id"]).execute()

    @reset_handler("delete_sent_message")
    def delete_sent_message(
        self,
        message_info: dict[str, Any],
    ) -> None:
        """Deletes the sent message with the given criteria."""
        sent_messages = self.search_messages(
            message_info=message_info, message_type="messages"
        )
        for sent_message in sent_messages:
            logger.debug(
                f"Deleting sent message with subject {sent_message['subject']}"
            )
            confirm_action(
                f"Deleting sent message with subject {sent_message['subject']}"
            )(self.delete_sent_message_by_id)(sent_message["id"])

    @reset_handler("send_message")
    def send_message(
        self,
        message_info: dict[str, Any],
    ) -> None:
        """Creates and sends an email message."""
        message = EmailMessage()
        message.set_content(message_info["body"])
        message["To"] = message_info.get("recipient", config.gmail_recipient)
        message["Subject"] = message_info["subject"]
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}

        @confirm_action(f"Sending the message {message_info}.")
        def _send():
            self.service.users().messages().send(
                userId="me", body=create_message
            ).execute()
            logger.debug("Message sent successfully.")

        logger.debug(f"Sending the message {message_info}.")
        _send()

    @reset_handler("mark_message_important")
    def mark_message_important(
        self,
        is_important: bool,
        subject_contains: str,
    ) -> None:
        """Marks the email with the given subject as important."""
        messages = (
            self.service.users()
            .messages()
            .list(userId="me", q=f"subject:{subject_contains}")
            .execute()
            .get("messages", [])
        )
        for message in messages:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message["id"], format="metadata")
                .execute()
            )
            if is_important:
                self.service.users().messages().modify(
                    userId="me", id=message["id"], body={"addLabelIds": ["IMPORTANT"]}
                ).execute()
            else:
                self.service.users().messages().modify(
                    userId="me",
                    id=message["id"],
                    body={"removeLabelIds": ["IMPORTANT"]},
                ).execute()

    def get_message(self, message_id: str) -> dict[str, Any]:
        """Retrieves the full message using the message ID."""
        raw_message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return get_message_from_raw(raw_message)

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

    def delete_draft_by_id(self, draft_id: str) -> None:
        """Deletes the draft with the given ID."""
        self.service.users().drafts().delete(userId="me", id=draft_id).execute()
        logger.debug("Draft deleted successfully.")

    def delete_sent_message_by_id(self, message_id: str) -> None:
        """Deletes the sent message with the given ID."""
        self.service.users().messages().delete(userId="me", id=message_id).execute()
        logger.debug(f"Sent message with id {message_id} deleted successfully.")
