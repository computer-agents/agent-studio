from typing import Any

from playground.desktop_env.eval.connectors.gspace.gdocs import GoogleDocsService
from playground.desktop_env.eval.evaluator import Evaluator


class GoogleDocsEvaluator(Evaluator):
    name: str = "google_docs"

    def __init__(
        self,
        reference_answer: dict,
        reset_procedure: list[dict],
        env_config: dict,
        eval_tag: str = "",
    ) -> None:
        super().__init__(
            reference_answer=reference_answer,
            reset_procedure=reset_procedure,
            env_config=env_config,
            eval_tag=eval_tag,
        )
        self.service = GoogleDocsService(
            credential_path=self.env_settings["credential_path"]
        )
        self.document_id: str = ""

    def execute(self, steps: list[dict[str, dict[str, Any]]]) -> bool:
        try:
            for step in steps:
                action, params = list(step.items())[0]
                # match action:
                #     case "create_document":
                #         # Code to create a new Google Docs document
                #     case "edit_document":
                #         # Code to edit a Google Docs document
                #     # Add other actions specific to Google Docs
                #     case _:
                #         raise Exception(
                #             f"Action {action} not supported by Google Docs"
                #         )
            return True
        except Exception as e:
            print(f"An error occurred in Google Docs env: {e}")
            return False

    def __call__(self) -> float:
        return 0.0
        # if self.env_settings is None:
        #     raise ValueError(f"env_settings for {self.name} is None")
        # calendar_id = self.env_settings["calendar_id"]
        # score = 1.0

        # try:
        #     for approach, value in self.reference_answer.items():
        #         match approach:
        #             case "event_match":
        #                 events: list[dict] = self.service.search_events_by_info(
        #                     value,
        #                     calendar_id=calendar_id,
        #                     # if calendar_id is None, fallback to primary calendar
        #                 )
        #                 if len(events) == 0:
        #                     score = 0.0
        #                 elif len(events) > 1:
        #                     raise ValueError(f"More than one event found: {events}")
        #                 else:
        #                     score *= 1.0
        #             case "check_event_exists":
        #                 """
        #                 Two parameters:
        #                 - event: the event to look for
        #                 - exists: whether the event should exist or not
        #                 """
        #                 events = self.service.list_events(
        #                     self.env_settings["calendar_id"]
        #                 )
        #                 score *= float(
        #                     self.check_event_exists(value["event"], events)
        #                     == value["exists"]
        #                 )
        # except Exception as e:
        #     print(f"An error occurred: {e}\nscore may be incorrect")
        #     score = 0.0

        # return score
