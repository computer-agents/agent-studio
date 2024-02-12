import logging
from datetime import datetime, timezone
from typing import Any

from playground.config import Config
from playground.env.desktop_env.eval.connectors.gservice import GoogleService
from playground.env.desktop_env.eval.evaluator import Evaluator, FeedbackException
from playground.utils.human_utils import confirm_action

config = Config()
logger = logging.getLogger(__name__)


def time_match(timestamp1: str, timestamp2: str) -> bool:
    """Checks if the pred time matches the ref time."""
    timestamp1 = timestamp1.replace("Z", "+00:00")
    timestamp2 = timestamp2.replace("Z", "+00:00")
    dt1 = datetime.fromisoformat(timestamp1).astimezone(timezone.utc)
    dt2 = datetime.fromisoformat(timestamp2).astimezone(timezone.utc)

    return dt1 == dt2


def event_match(
    event1: dict,
    event2: dict,
) -> bool:
    """Checks if the event2 matches the event1."""
    for key, value in event1.items():
        pred_value = event2.get(key, None)
        if key in ["summary", "description", "location"]:
            if value != pred_value:
                return False
        elif key in ["start", "end"]:
            if not (
                "dateTime" in value
                and "dateTime" in pred_value
                and time_match(value["dateTime"], pred_value["dateTime"])
            ):
                return False
    return True


class GoogleCalendarService(GoogleService):
    def __init__(self) -> None:
        super().__init__(
            scopes=[
                "https://www.googleapis.com/auth/calendar",
            ],
            service_name="calendar",
            service_version="v3",
        )

    def create_event(
        self,
        event_info: dict[str, Any],
    ) -> None:
        """Creates an event on the calendar."""
        self.service.events().insert(
            calendarId=config.google_calendar_id, body=event_info
        ).execute()

    def list_events(self) -> list[dict]:
        """Lists all events on the calendar."""
        events = []
        page_token = None
        while True:
            events_result = (
                self.service.events()
                .list(calendarId=config.google_calendar_id, pageToken=page_token)
                .execute()
            )
            events.extend(events_result["items"])
            page_token = events_result.get("nextPageToken")
            if not page_token:
                break
        return events

    def search_events_by_time_range(
        self,
        start_time: str,
        end_time: str,
    ) -> list[dict[str, Any]]:
        """Searches for events that fall within the given time range."""
        events = []
        page_token = None
        while True:
            events_result = (
                self.service.events()
                .list(
                    calendarId=config.google_calendar_id,
                    timeMin=start_time,
                    timeMax=end_time,
                    singleEvents=True,
                )
                .execute()
            )
            events.extend(events_result["items"])
            page_token = events_result.get("nextPageToken")
            if not page_token:
                break
        return events

    def search_events(self, event_info: dict[str, Any]) -> list[dict[str, str]]:
        """Searches for events that match the reference event."""
        events = self.search_events_by_time_range(
            start_time=event_info["start"]["dateTime"],
            end_time=event_info["end"]["dateTime"],
        )
        results = []
        for event in events:
            if event_match(event_info, event):
                results.append(event)
        return results

    @confirm_action
    def delete_event_by_id(self, event_id: str) -> None:
        """Deletes an event on the calendar."""
        self.service.events().delete(
            calendarId=config.google_calendar_id, eventId=event_id
        ).execute()
        logger.info(f"Event with ID {event_id} has been deleted.")

    def delete_event(
        self,
        event_info: dict[str, Any],
    ) -> None:
        """Deletes events that match the given event."""
        events = self.search_events_by_time_range(
            start_time=event_info["start"]["dateTime"],
            end_time=event_info["end"]["dateTime"],
        )
        for event in events:
            if event_match(event_info, event):
                logger.info(f"Deleting event: {event['summary']}")
                self.delete_event_by_id(event["id"])

    def clear_calendar(self) -> None:
        """Deletes all events on the calendar."""

        @confirm_action
        def _clear_calendar() -> None:
            events = self.list_events()
            for event in events:
                self.service.events().delete(
                    calendarId=config.google_calendar_id, eventId=event["id"]
                ).execute()
            logger.info("All events have been deleted.")

        logger.info("Clearing all events on the calendar")
        _clear_calendar()

    def check_event_exists(
        self,
        event_info: dict[str, Any],
        exists: bool,
    ) -> None:
        """Checks if the given event exists."""
        events = self.search_events(event_info)
        event_exists = len(events) > 0

        if event_exists != exists:
            raise FeedbackException(
                f"The error occured when checking the existence of {event_info}. "
                f"It should be {exists}."
            )


class GoogleCalendarEvaluator(Evaluator):
    name: str = "google_calendar"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = GoogleCalendarService()
        self.evaluation_handlers = {
            "check_event_exists": self.service.check_event_exists,
        }
        self.reset_handlers = {
            "create_event": self.service.create_event,
            "delete_event": self.service.delete_event,
            "clear_calendar": self.service.clear_calendar,
        }
