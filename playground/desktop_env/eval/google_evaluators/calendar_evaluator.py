import logging
from datetime import datetime, timezone
from typing import Any

from playground.config import Config
from playground.desktop_env.eval.connectors.gspace.gcalendar import (
    GoogleCalendarService,
)
from playground.desktop_env.eval.evaluator import Evaluator

config = Config()
logger = logging.getLogger(__name__)


class GoogleCalendarEvaluator(Evaluator):
    name: str = "google_calendar"

    def __init__(
        self,
        reference_answer: dict,
        reset_procedure: list[dict],
        eval_tag: str = "",
    ) -> None:
        super().__init__(
            reference_answer=reference_answer,
            reset_procedure=reset_procedure,
            eval_tag=eval_tag,
        )
        self.service = GoogleCalendarService()
        self.events: dict = {}

    @staticmethod
    def item_match(ref: str | None, pred: str | None) -> float:
        return float(pred == ref)

    @staticmethod
    def list_match(ref: list, pred: list) -> float:
        score = 1.0
        for i in range(len(ref)):
            match_score = 0.0
            for j in range(len(pred)):
                if isinstance(ref[i], dict):
                    match_score = GoogleCalendarEvaluator.dict_match_left(
                        ref=ref[i], pred=pred[j]
                    )
                else:
                    match_score = GoogleCalendarEvaluator.item_match(
                        ref=ref[i], pred=pred[j]
                    )
                if match_score > 0.0:
                    break
            score *= match_score
        return score

    @staticmethod
    def time_match(timestamp1: str, timestamp2: str) -> float:
        """Checks if the pred time matches the ref time."""
        timestamp1 = timestamp1.replace("Z", "+00:00")
        timestamp2 = timestamp2.replace("Z", "+00:00")
        dt1 = datetime.fromisoformat(timestamp1).astimezone(timezone.utc)
        dt2 = datetime.fromisoformat(timestamp2).astimezone(timezone.utc)

        return dt1 == dt2

    @staticmethod
    def dict_match_left(
        ref: dict[str, str] | dict[str, list] | dict[str, dict],
        pred: dict[str, str] | dict[str, list] | dict[str, dict],
    ) -> float:
        """
        Checks if the pred dict matches the ref dict. Only checks the keys in ref.
        :param ref: The reference dict.
        :param pred: The dict to be checked.
        :return: 1.0 if the dicts match, 0.0 otherwise.
        """
        score = 1.0
        for key, item in ref.items():
            pred_item = pred.get(key, None)
            if isinstance(item, dict) and isinstance(pred_item, dict):
                score *= GoogleCalendarEvaluator.dict_match_left(
                    ref=item, pred=pred_item
                )
            elif isinstance(item, list) and isinstance(pred_item, list):
                score *= GoogleCalendarEvaluator.list_match(ref=item, pred=pred_item)
            elif isinstance(item, (str, int, float)) and isinstance(
                pred_item, (str, int, float)
            ):
                score *= GoogleCalendarEvaluator.item_match(ref=item, pred=pred_item)
            else:
                return 0.0
        return score

    @staticmethod
    def check_event_exists(reference_event: dict, actual_events: list[dict]) -> bool:
        """
        Checks if a given event exists in the list of actual events.
        :param reference_event: The event to look for.
        :param actual_events: list of events to search within.
        :return: True if the event exists, False otherwise.
        """
        for event in actual_events:
            if GoogleCalendarEvaluator.dict_match_left(reference_event, event):
                return True
        return False

    def execute(
        self, steps: list[dict[str, dict[str, Any]]], response: str | None = None
    ) -> float:
        score = 1.0
        for step in steps:
            for action, params in step.items():
                match action:
                    # case "create_and_cd_calendar":
                    #     calendar = self.service.create_calendar(params)
                    #     config.google_calendar_id = calendar["id"]
                    # case "cd_calendar":
                    #     if params["id"] != "primary":
                    #         calendar = self.service.find_calendar_by_id(
                    #             params["id"]
                    #         )
                    #         if calendar == {}:
                    #             raise Exception(
                    #                 f"Calendar {params['id']} not found"
                    #             )
                    #         config.google_calendar_id = calendar["id"]
                    #     else:
                    #         config.google_calendar_id = "primary"
                    case "clear_calendar":
                        self.service.clear_calendar(config.google_calendar_id)
                    case "create_event":
                        event = self.service.create_event(
                            start_time=params["start"]["dateTime"],
                            end_time=params["end"]["dateTime"],
                            summary=params.get("summary"),
                            location=params.get("location"),
                            description=params.get("description"),
                            attendees=params.get("attendees"),
                            calendar_id=config.google_calendar_id,
                        )
                        self.events[event.get("id")] = event
                    case "deduplicate_event":
                        events = self.service.search_events_by_time_range(
                            start_time=params["start"]["dateTime"],
                            end_time=params["end"]["dateTime"],
                            calendar_id=config.google_calendar_id,
                        )
                        for event in events:
                            if (
                                event["summary"] == params["summary"]
                                and (
                                    ("location" not in params)
                                    or (event["location"] == params["location"])
                                )
                                and (
                                    ("description" not in params)
                                    or (event["description"] == params["description"])
                                )
                                and self.time_match(
                                    event["start"]["dateTime"],
                                    params["start"]["dateTime"],
                                )
                                and self.time_match(
                                    event["end"]["dateTime"],
                                    params["end"]["dateTime"],
                                )
                            ):
                                self.service.delete_event(
                                    event_id=event["id"],
                                    calendar_id=config.google_calendar_id,
                                )
                    # case "delete_cur_calendar":
                    #     self.service.delete_calendar(
                    #         config.google_calendar_id
                    #     )
                    case "event_match":
                        events = self.service.search_events_by_info(
                            params,
                        )
                        if len(events) == 0:
                            score = 0.0
                        elif len(events) > 1:
                            raise ValueError(f"More than one event found: {events}")
                        else:
                            score *= 1.0
                    case "check_event_exists":
                        """
                        Two parameters:
                        - event: the event to look for
                        - exists: whether the event should exist or not
                        """
                        events = self.service.list_events(config.google_calendar_id)
                        score *= float(
                            self.check_event_exists(params["event"], events)
                            == params["exists"]
                        )
                    case _:
                        raise Exception(
                            f"Action {action} not supported by Google calendar"
                        )

        return score
