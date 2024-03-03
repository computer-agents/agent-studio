import logging
import time
from io import BytesIO

from pyrogram.client import Client
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from playground.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)

config = Config()


class TelegramService:
    def __init__(self) -> None:
        self.__app_id: str | int = config.telegram_api_id
        self.__app_hash: str = config.telegram_api_hash
        self.__service = Client(
            "playground_account",
            self.__app_id,
            self.__app_hash,
            workdir=config.telegram_workdir
            if hasattr(config, "telegram_workdir")
            else "playground/config",
        )

    def __get_message_type(self, message) -> str:
        if message.text:
            return "text"
        elif message.photo:
            return "photo"
        elif message.document:
            return "document"
        elif message.video:
            return "video"
        return "unknown"

    def message_match(self, chat_id: int | str, ref_messages: list[dict]) -> None:
        def _match_text(text: str, ref_messages: dict):
            compare_method = ref_messages.get("compare_method", "")
            if compare_method == "exact":
                return text == ref_messages.get("value", "")
            else:
                return False

        def _match_one_message(message: Message, ref_message: dict, message_type: str):
            if (ref_message.get("replyto", None) is None) != (
                message.reply_to_message_id is None
            ):
                raise FeedbackException(
                    f"The error occured when checking the message with {chat_id}. "
                    f"Replyto message does not match."
                    f"Expect {ref_message.get('replyto')}, "
                    f"but get {message.reply_to_message_id}"
                )
            elif ref_message.get("replyto", None) is not None:
                replyto_ref = ref_message.get("replyto")
                if replyto_ref is None or message.reply_to_message_id is None:
                    raise LookupError(
                        f"Can't find the replyto message "
                        f"for the message with {chat_id} "
                        f"Find message: {message}"
                        f"Reference message: {ref_message}"
                    )
                replyto_message = self.__service.get_chat_history(
                    message.chat.id,
                    limit=1,
                    offset_id=message.reply_to_message_id + 1,
                )
                replyto_message = next(replyto_message)
                _match_one_message(
                    replyto_message,
                    replyto_ref,
                    # recersively verify all replyto messages
                    self.__get_message_type(replyto_message),
                )
            match message_type:
                case "text":
                    if not _match_text(message.text, ref_message):
                        raise FeedbackException(
                            f"The error occured "
                            f"when checking the message with {chat_id}. "
                            f"Text message does not match."
                            f"Expect {ref_message.get('value')}, but get {message.text}"
                        )
                case "document":
                    downloaded_file = self.__service.download_media(
                        message.document.file_id,
                        file_name=message.document.file_name,
                        in_memory=True,
                    )
                    if not isinstance(downloaded_file, BytesIO):
                        raise LookupError(
                            f"File {message.document.file_name} not found. "
                            f"Failed to download"
                        )

                    with open(ref_message.get("file_path", ""), "rb") as f:
                        file_ref = BytesIO(f.read())

                    if downloaded_file.getvalue() != file_ref.getvalue():
                        raise FeedbackException(
                            f"The error occured when "
                            f"checking the message with {chat_id}. "
                            f"Document file does not match."
                        )
                # Extend here for other types like 'photo', 'video', etc.
                case _:
                    raise FeedbackException(
                        f"The error occured when checking the message with {chat_id}. "
                        f"Message type {message_type} not supported."
                    )

        with self.__service:
            messages = self.__service.get_chat_history(chat_id, limit=len(ref_messages))
            messages = [message for message in messages]

            # messages returned from the API are in reverse chronological order
            # so we need to reverse the reference messages
            for message, ref_message in zip((messages), reversed(ref_messages)):
                message_type = self.__get_message_type(message)

                if message_type != ref_message.get("type"):
                    raise FeedbackException(
                        f"The error occured when checking the message with {chat_id}. "
                        f"Message type does not match"
                        f"Expect {ref_message.get('type')}, but get {message_type}"
                    )

                _match_one_message(message, ref_message, message_type)

    def delete_recent_messages(self, chat_id: str | int, n: int) -> None:
        @confirm_action(
            f"Are you sure you want to delete {n} recent messages from {chat_id}"
        )
        def _delete_recent_messages(chat_id: str | int, n: int) -> bool:
            with self.__service:
                messages = self.__service.get_chat_history(chat_id, limit=n)
                message_ids = [message.id for message in messages]

                try:
                    self.__service.delete_messages(chat_id, message_ids)
                    return True
                except FloodWait:
                    logger.warning("Rate limit exceeded. Sleeping for 1 seconds.")
                    time.sleep(1)
                    return False
                except Exception as e:
                    # Handle other possible exceptions
                    print(f"An error occurred: {e}")
                    return False

        _delete_recent_messages(chat_id, n)

    def _get_last_message_id(self, chat_id: str | int) -> int:
        """
        Must be called within a context manager (with self.__service).
        """
        messages = self.__service.get_chat_history(chat_id, limit=1)
        return next(messages).id

    def send_messages(
        self,
        chat_id: str | int,
        messages: list[str],
        replyto_offset: int | None = None,
    ):
        with self.__service:
            if replyto_offset is not None:
                replyto_message_id = self._get_last_message_id(chat_id) - replyto_offset
            else:
                replyto_message_id = None
            for message in messages:
                self.__service.send_message(
                    chat_id=chat_id,
                    text=message,
                    reply_to_message_id=replyto_message_id,
                )

    def send_document(
        self,
        chat_id: str | int,
        file_path: str,
        caption: str,
        replyto_offset: int | None = None,
    ):
        with self.__service:
            if replyto_offset is not None:
                replyto_message_id = self._get_last_message_id(chat_id) - replyto_offset
            else:
                replyto_message_id = None
            self.__service.send_document(
                chat_id,
                file_path,
                caption=caption,
                force_document=True,
                reply_to_message_id=replyto_message_id,
            )


class TelegramEvaluator(Evaluator):
    name: str = "telegram"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = TelegramService()

    @evaluation_handler("message_match")
    def message_match(self, chat_id: str | int, ref_messages: list[dict]) -> None:
        """
        Check if the messages in the chat match the reference messages.

        Args:
            chat_id (str | int): Chat id.
            ref_messages (list[dict]): List of reference messages.
                Each reference message is a dictionary with the following keys:

                - type (str): Type of the message. \
                    valid values are 'text', 'document'.
                - compare_method (str): Method to compare the message. \
                    Supported methods is 'exact'.
                - value (str): Value to compare with the message. \
                    Only used when compare_method is 'exact'.
                - file_path (str, optional): Path to the file. \
                    Only used when type is 'document'.
                - caption (str, optional): Caption of the file. \
                    Only used when type is 'document'.
                - replyto (dict, optional): Reference message to reply to. \
                    Required keys are the same as the ref_messages \
                    (for recursive matching).

        Raises:
            FeedbackException: If the messages do not match.

        Returns:
            None

        Example::

            ref_messages = [
                {
                    "type": "text",
                    "compare_method": "exact",
                    "value": "Welcome to the playground!",
                },
                {
                    "type": "document",
                    "file_path": "playground_data/test/telegram/GitHub-logo.png",
                    "caption": "GitHub logo.",
                    "replyto": {
                        "type": "text",
                        "compare_method": "exact",
                        "value": "hi",
                    }
                }
            ]
        """
        self.service.message_match(chat_id, ref_messages)

    @reset_handler("send_messages")
    def send_messages(self, chat_id: str | int, messages: list[str]):
        """
        Send a message to specific chat.

        Args:
            chat_id (str | int): Chat id.
            messages (list[str]): List of messages to be sent.
                messages are in the order of sending.

        Returns:
            None
        """
        self.service.send_messages(chat_id, messages)

    @reset_handler("delete_recent_messages")
    def delete_recent_messages(
        self,
        chat_id: str | int,
        n: int,
    ):
        """
        Delete recent messages from specific chat.

        Args:
            chat_id (str | int): Chat id.
            n (int): Number of messages to be deleted.

        Returns:
            None
        """
        self.service.delete_recent_messages(
            chat_id=chat_id,
            n=n,
        )

    @reset_handler("send_document")
    def send_document(
        self,
        chat_id: str | int,
        file_path: str,
        caption: str = "",
        replyto_offset: int | None = None,
    ):
        """
        Send a document to specific chat.

        Args:
            chat_id (str | int): Chat id.
            file_path (str): Path to the document.
            caption (str, optional): Caption of the document. Defaults to "".
            replyto_offset (int, optional): Offset of the message to reply to. \
                Defaults to None. The offset is counted from the last message. \
                E.g. 0 means reply to the last message, \
                1 means reply to the second last message, etc.

        Returns:
            None
        """
        self.service.send_document(
            chat_id=chat_id,
            file_path=file_path,
            caption=caption,
            replyto_offset=replyto_offset,
        )
