from typing import Union

from desktop_env.eval.envs.gspace.gcalendar import GoogleCalendarService
from desktop_env.eval.evaluator import Evaluator


class GoogleCalendarEvaluator(Evaluator):
    @staticmethod
    def evaluator_name() -> str:
        return "google_calendar"

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

    def __call__(self) -> float:
        if self.env_configs is None:
            raise ValueError(f"env_configs for {self.evaluator_name()} is None")
        if self.extra_info is None:
            raise ValueError(f"extra_info for {self.evaluator_name()} is None")
        gcalendar_service = GoogleCalendarService(
            token_path=self.env_configs["token_path"]
        )
        calendar_id = self.extra_info["calendar_id"]
        score = 1.0

        try:
            for approach, value in self.reference_answer.items():
                match approach:
                    case "event_match":
                        pred = gcalendar_service.search_events(
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
                            score *= self.dict_match_left(value, pred[0])
        except Exception as e:
            print(f"An error occurred: {e}\nscore may be incorrect")
            score = 0.0

        return score
