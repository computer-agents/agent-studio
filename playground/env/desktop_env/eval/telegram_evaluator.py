import logging
import time

from pyrogram.client import Client
from pyrogram.errors import FloodWait

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import Evaluator, FeedBackException
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
        with self.__service:
            messages = self.__service.get_chat_history(
                chat_id, limit=len(ref_messages)
            )
            messages = [message for message in messages]

            # messages returned from the API are in reverse chronological order
            # so we need to reverse the reference messages
            for message, ref_message in zip(messages, reversed(ref_messages)):
                message_type = self.__get_message_type(message)

                if message_type == ref_message.get("type"):
                    if message_type == "text" and self.match_text(
                        message.text, ref_message
                    ):
                        continue
                    else:
                        raise FeedBackException(
                            f"The error occured when checking the message with {chat_id}. "
                            f"Text message does not match."
                            f"Expect {ref_message.get('value')}, but get {message.text}"
                        )
                    # Extend here for other types like 'photo', 'document', etc.
                else:
                    raise FeedBackException(
                        f"The error occured when checking the message with {chat_id}. "
                        f"Message type does not match"
                        f"Expect {ref_message.get('type')}, but get {message_type}"
                    )


    def match_text(self, text: str, ref_messages: dict):
        compare_method = ref_messages.get("compare_method", "")
        if compare_method == "exact":
            return text == ref_messages.get("value", "")
        else:
            return False

    def send_message(self, chat_id: str | int, message: str):
        with self.__service:
            self.__service.send_message(chat_id, message)

    def delete_recent_messages(self, chat_id: str | int, n: int):
        @confirm_action
        def _delete_recent_messages(chat_id: str | int, n: int):
            with self.__service:
                messages = self.__service.get_chat_history(chat_id, limit=n)
                message_ids = [message.id for message in messages]

                try:
                    self.__service.delete_messages(chat_id, message_ids)
                    return True
                except FloodWait:
                    logger.warn("Rate limit exceeded. Sleeping for 1 seconds.")
                    time.sleep(1)
                    return False
                except Exception as e:
                    # Handle other possible exceptions
                    print(f"An error occurred: {e}")
                    return False

        print(f"Are you sure you want to delete {n} recent messages from {chat_id}")
        _delete_recent_messages(chat_id, n)


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
        self.evaluation_handlers = {
            "message_match": self.service.message_match,
        }
        self.reset_handlers = {
            "send_message": self.service.send_message,
            "delete_recent_messages": self.service.delete_recent_messages,
        }
