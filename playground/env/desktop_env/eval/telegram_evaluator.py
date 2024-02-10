import time
import logging

from pyrogram import Client
from pyrogram.errors import FloodWait

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import Evaluator
from playground.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)

config = Config()

class TelegramService:
    def __init__(self) -> None:
        self.__app_id: str = config.telegram_api_id
        self.__app_hash: str = config.telegram_api_hash
        self.__service = Client(
            "playground_account",
            self.__app_id,
            self.__app_hash,
            workdir=config.telegram_workdir if hasattr(config, "telegram_workdir") else "playground/config",
        )
        self.__service.start()

    def __del__(self) -> None:
        self.__service.stop()

    def __get_message_type(self, message) -> str:
        if message.text:
            return 'text'
        elif message.photo:
            return 'photo'
        elif message.document:
            return 'document'
        elif message.video:
            return 'video'
        return 'unknown'

    def message_match(self, chat_id: int | str, ref_messages: list[dict]):
        messages = self.__service.get_chat_history(chat_id, limit=len(ref_messages))

        # messages returned from the API are in reverse chronological order
        # so we need to reverse the reference messages
        for message, ref_messages in zip(messages, reversed(ref_messages)):
            message_type = self.__get_message_type(message)

            if message_type == ref_messages.get("type"):
                if message_type == 'text' and self.match_text(message.text, ref_messages):
                    continue
                else:
                    return False
                # Extend here for other types like 'photo', 'document', etc.
            else:
                return False

        return True

    def match_text(self, text, ref_messages):
        compare_method = ref_messages.get("compare_method", "")
        if compare_method == "exact":
            return text == ref_messages.get("value", "")
        else:
            return False

    def send_message(self, chat_id, message):
        self.__service.send_message(chat_id, message)

    def delete_recent_messages(self, chat_id, n):
        @confirm_action
        def _delete_recent_messages(chat_id, n):
            messages = self.__service.get_chat_history(chat_id, limit=n)
            message_ids = [message.id for message in messages]

            try:
                self.__service.delete_messages(chat_id, message_ids)
                return True
            except FloodWait as e:
                # Handle the case where too many requests are sent to the Telegram API
                logger.warn(f"Rate limit exceeded. Sleeping for {e.x} seconds.")
                time.sleep(e.x)
                return False
            except Exception as e:
                # Handle other possible exceptions
                print(f"An error occurred: {e}")
                return False

        print(f"Deleting {n} recent messages from {chat_id}")
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
        self.feedback_handlers = {
            "message_match": lambda chat_id, ref_messages: (
                f"The error occured when checking the message with {chat_id}. "
                f"It should be {ref_messages}."
            )
        }
