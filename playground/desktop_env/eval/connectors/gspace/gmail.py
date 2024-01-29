import base64
import logging

# import mimetypes
from email.message import EmailMessage

from googleapiclient.errors import HttpError

from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService

logger = logging.getLogger(__name__)
SEND = 1
DELETE = 2


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

    def get_message(self, message_id):
        # Retrieve the full message using the message ID
        try:
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            return message
        except HttpError as err:
            print(err)
            return None

    def get_subject(self, message):
        headers = message["payload"]["headers"]
        subject = next(
            header["value"] for header in headers if header["name"].lower() == "subject"
        )
        return subject

    def get_attachment_name(self, message):
        if "parts" not in message["payload"]:
            return None

        for part in message["payload"]["parts"]:
            if part["filename"] != "":
                logger.error(f"filename: {part['filename']}")
                return part["filename"]

        return None

    def get_cc(self, message):
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
        # Decode the body content
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
        headers = message["payload"]["headers"]
        recipient = next(
            header["value"] for header in headers if header["name"].lower() == "to"
        )
        return recipient

    def create_draft(
        self,
        subject: str,
        recipient: str,
        content: str,
    ):
        try:
            message = EmailMessage()
            message.set_content(content)  # "This is automated draft mail"
            message["To"] = recipient  # "gduser1@workspacesamples.dev"
            message["Subject"] = subject  # "Automated draft"

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"message": {"raw": encoded_message}}
            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=create_message)
                .execute()
            )

            logger.info(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            draft = None

        return draft

    def get_recent_draft(self) -> dict[str, str] | None:
        # List all drafts
        results = self.service.users().drafts().list(userId="me").execute()
        drafts = results.get("drafts", [])

        if not drafts:
            logger.warn("No drafts found.")
            return None

        # Assuming the most recent draft is the first in the list
        recent_draft_id = drafts[0]["id"]

        # Retrieve the most recent draft
        draft = (
            self.service.users().drafts().get(userId="me", id=recent_draft_id).execute()
        )
        message_id = draft["message"]["id"]
        message = self.get_message(message_id)
        subject = self.get_subject(message)
        recipient = self.get_recipient(message)
        decoded_body = self.get_body(message)
        attachment_name = self.get_attachment_name(message)
        cc = self.get_cc(message)

        return {
            "id": recent_draft_id,
            "subject": subject,
            "recipient": recipient,
            "body": decoded_body,
            "attachment": attachment_name,
            "cc": cc,
        }

    def get_recent_sent_mail(self) -> dict[str, str] | None:
        # List all sent mails
        results = (
            self.service.users()
            .messages()
            .list(userId="me", labelIds=["SENT"])
            .execute()
        )
        sent_mails = results.get("messages", [])
        if not sent_mails:
            logger.warn("No sent mails found.")
            return None

        # Assuming the most recent sent mail is the first in the list
        recent_sent_mail_id = sent_mails[0]["id"]

        # Retrieve the most recent sent mail
        sent_mail = (
            self.service.users()
            .messages()
            .get(userId="me", id=recent_sent_mail_id)
            .execute()
        )
        message_id = sent_mail["id"]
        message = self.get_message(message_id)
        subject = self.get_subject(message)
        recipient = self.get_recipient(message)
        decoded_body = self.get_body(message)
        attachment_name = self.get_attachment_name(message)

        return {
            "id": recent_sent_mail_id,
            "subject": subject,
            "recipient": recipient,
            "body": decoded_body,
            "attachment": attachment_name,
        }

    def delete_draft(self, draft_id: str) -> bool:
        try:
            self.service.users().drafts().delete(userId="me", id=draft_id).execute()
            logger.info(f"Draft with id {draft_id} deleted successfully.")
            return True
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False

    def delete_sent_email(self, sent_email_id: str) -> bool:
        try:
            email_to_delete = self.get_message(sent_email_id)
            subject = self.get_subject(email_to_delete)
            recipient = self.get_recipient(email_to_delete)
            snippet = email_to_delete["snippet"]
            logger.info(
                f"The email to delete:\nSubject: {subject}\n"
                f"Recipient: {recipient}\nSnippet: {snippet}"
            )
            if self._confirm(DELETE):
                self.service.users().messages().delete(
                    userId="me", id=sent_email_id
                ).execute()
                logger.info(f"Sent email with id {sent_email_id} deleted successfully.")
                return True
            return False
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return False

    # def create_draft_with_attachment(
    #     self,
    #     content: str,
    #     sender: str,
    #     recipient: str,
    #     subject: str,
    #     attachment_filename: str,
    # ):
    #     """Create and insert a draft email with attachment.
    #     Print the returned draft's message and id.
    #     Returns: Draft object, including draft id and message meta data.
    #     """
    #     try:
    #         mime_message = EmailMessage()

    #         # headers
    #         mime_message["To"] = recipient  # "gduser1@workspacesamples.dev"
    #         mime_message["From"] = sender  # "gduser2@workspacesamples.dev"
    #         mime_message["Subject"] = subject  # "sample with attachment"

    #         # text
    #         mime_message.set_content(content)
    # "Hi, this is automated mail with attachment.Please do not reply."

    #         # guessing the MIME type
    #         type_subtype, _ = mimetypes.guess_type(attachment_filename)
    #         maintype, subtype = type_subtype.split("/")

    #         with open(attachment_filename, "rb") as fp:
    #             attachment_data = fp.read()
    #         mime_message.add_attachment(attachment_data, maintype, subtype)

    #         encoded_message = base64.urlsafe_b64encode(
    # mime_message.as_bytes()).decode()

    #         create_draft_request_body = {"message": {"raw": encoded_message}}
    #         draft = (
    #             self.service.users()
    #             .drafts()
    #             .create(userId="me", body=create_draft_request_body)
    #             .execute()
    #         )
    #         print(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')
    #     except HttpError as error:
    #         print(f"An error occurred: {error}")
    #         draft = None

    #     return draft

    # def build_file_part(file):
    #     """Creates a MIME part for a file.

    #     Args:
    #         file: The path to the file to be attached.

    #     Returns:
    #         A MIME part that can be attached to a message.
    #     """
    #     content_type, encoding = mimetypes.guess_type(file)

    #     if content_type is None or encoding is not None:
    #         content_type = "application/octet-stream"
    #     main_type, sub_type = content_type.split("/", 1)
    #     if main_type == "text":
    #         with open(file, "rb"):
    #         msg = MIMEText("r", _subtype=sub_type)
    #     elif main_type == "image":
    #         with open(file, "rb"):
    #         msg = MIMEImage("r", _subtype=sub_type)
    #     elif main_type == "audio":
    #         with open(file, "rb"):
    #         msg = MIMEAudio("r", _subtype=sub_type)
    #     else:
    #         with open(file, "rb"):
    #         msg = MIMEBase(main_type, sub_type)
    #         msg.set_payload(file.read())
    #     filename = os.path.basename(file)
    #     msg.add_header("Content-Disposition", "attachment", filename=filename)

    #     return msg

    def _confirm(self, type=SEND):
        if type == SEND:
            words = ["send", "Sending", "sent"]
        elif type == DELETE:
            words = ["delete", "Deleting", "deleted"]
        else:
            raise Exception(f"Type {type} not supported by Gmail")

        user_input = (
            input(f"Do you want to {words[0]} the email? (y/n): ").strip().lower()
        )
        if user_input == "y":
            logger.info(f"{words[1]} email...")
            return True
        logger.info(f"Email not {words[2]}. Evaluation results may be incorrect.")
        return False

    def send_message(
        self,
        content: str,
        recipient: str,
        subject: str,
        sender: str = "",
    ):
        """Create and send an email message
        Print the returned  message id
        Returns: Message object, including message id
        """
        # TODO: should examine the agent behavior before sending
        # TODO: prompt the user to confirm before sending, like in open interpreter
        try:
            message = EmailMessage()
            message.set_content(content)  # "This is automated draft mail"
            message["To"] = recipient  # "gduser1@workspacesamples.dev"
            if sender == "":
                message["From"] = (
                    self.service.users()
                    .getProfile(userId="me")
                    .execute()["emailAddress"]
                )
            else:
                message["From"] = sender  # "gduser2@workspacesamples.dev"
            message["Subject"] = subject  # "Automated draft"

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            # prompt the user to confirm before sending
            if self._confirm(SEND):
                # if True:
                send_message = (
                    self.service.users()
                    .messages()
                    .send(userId="me", body=create_message)
                    .execute()
                )
                print(f'Message Id: {send_message["id"]}')
            else:
                send_message = None
        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None

        return send_message
