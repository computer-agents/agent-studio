from datetime import datetime
from typing import Union

from desktop_env.eval.bridges.gspace.gcalendar import GoogleCalendarService
from desktop_env.eval.evaluator import Evaluator


class GoogleCalendarEvaluator(Evaluator):
    name: str = "google_calendar"

    def __init__(
        self,
        reference_answer: dict,
        reset_actions: list[dict],
        env_config: dict,
        eval_tag: str = "",
    ) -> None:
        super().__init__(reference_answer, reset_actions, env_config, eval_tag)
        self.service = GoogleCalendarService(token_path=self.env_settings["token_path"])
        self.events: dict = {}

    @staticmethod
    def item_match(ref: str | None, pred: str | None) -> float:
        # print(f"ref: {ref}, pred: {pred}")
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
    def dict_match_left(
        ref: Union[dict[str, str], dict[str, list], dict[str, dict]],
        pred: Union[dict[str, str], dict[str, list], dict[str, dict]],
    ) -> float:
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
    def to_utc(time: str) -> str:
        return datetime.fromisoformat(time).astimezone().isoformat()

    def execute(self, steps: list[dict]) -> bool:
        try:
            for step in steps:
                action: str
                params: dict
                for action, params in step.items():
                    match action:
                        # case "create_and_cd_calendar":
                        #     calendar = self.service.create_calendar(params)
                        #     self.env_settings["calendar_id"] = calendar["id"]
                        # case "cd_calendar":
                        #     if params["id"] != "primary":
                        #         calendar = self.service.find_calendar_by_id(
                        #             params["id"]
                        #         )
                        #         if calendar == {}:
                        #             raise Exception(
                        #                 f"Calendar {params['id']} not found"
                        #             )
                        #         self.env_settings["calendar_id"] = calendar["id"]
                        #     else:
                        #         self.env_settings["calendar_id"] = "primary"
                        case "clear_calendar":
                            self.service.clear_calendar(
                                self.env_settings["calendar_id"]
                            )
                        case "create_event":
                            event = self.service.create_event(
                                params.get("summary"),
                                params.get("location"),
                                params.get("description"),
                                params["start"]["dateTime"],
                                params["end"]["dateTime"],
                                params.get("attendees"),
                                self.env_settings["calendar_id"],
                            )
                            self.events[event.get("id")] = event
                        # case "delete_cur_calendar":
                        #     self.service.delete_calendar(
                        #         self.env_settings["calendar_id"]
                        #     )
                        case _:
                            raise Exception(
                                f"Action {action} not supported by Google calendar"
                            )
            return True
        except Exception as e:
            print(f"An error occurred in Google calendar env: {e}")
            return False

    def __call__(self) -> float:
        if self.env_settings is None:
            raise ValueError(f"env_settings for {self.name} is None")
        calendar_id = self.env_settings["calendar_id"]
        score = 1.0

        try:
            for approach, value in self.reference_answer.items():
                match approach:
                    case "event_match":
                        pred: list[dict] = self.service.search_events(
                            value["start"]["dateTime"],
                            value["end"]["dateTime"],
                            calendar_id=calendar_id,
                            # if calendar_id is None, fallback to primary calendar
                        )
                        if len(pred) == 0:
                            score = 0.0
                        elif len(pred) > 1:
                            raise ValueError(f"More than one event found: {pred}")
                        else:
                            pred[0]["start"]["dateTime"] = self.to_utc(
                                pred[0]["start"]["dateTime"]
                            )
                            pred[0]["end"]["dateTime"] = self.to_utc(
                                pred[0]["end"]["dateTime"]
                            )
                            value["start"]["dateTime"] = self.to_utc(
                                value["start"]["dateTime"]
                            )
                            value["end"]["dateTime"] = self.to_utc(
                                value["end"]["dateTime"]
                            )
                            score *= self.dict_match_left(value, pred[0])
        except Exception as e:
            print(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
