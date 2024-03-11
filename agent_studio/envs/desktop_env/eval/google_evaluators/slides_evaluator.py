import logging

from agent_studio.envs.desktop_env.eval.connectors.gservice import GoogleService
from agent_studio.envs.desktop_env.eval.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.envs.desktop_env.eval.google_evaluators.drive_evaluator import (
    GoogleDriveService,
)

logger = logging.getLogger(__name__)


class GoogleSlidesEvaluator(Evaluator):
    name: str = "google_slides"

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
            scopes=["https://www.googleapis.com/auth/presentations"],
            service_name="slides",
            service_version="v1",
        ).service
        self.drive_service = GoogleDriveService()

    def get_presentation(self, presentation_id: str) -> dict:
        """Gets the Google Slides presentation by its ID."""
        presentation = (
            self.service.presentations().get(presentationId=presentation_id).execute()
        )
        return presentation

    def get_presentation_title(self, presentation_id: str) -> str:
        """Gets the title of the Google Slides presentation."""
        presentation = self.get_presentation(presentation_id)
        if presentation:
            return presentation.get("title", "")
        return ""

    def add_slide(self, presentation_id: str, page_id: str | None = None) -> None:
        """Adds a new slide to the Google Slides presentation."""
        requests = [
            {
                "createSlide": {
                    "objectId": page_id,
                }
            }
        ]
        self.service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()

    def create_textbox(
        self,
        presentation_id: str,
        slide_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> str | None:
        """Creates a textbox on the Google Slides presentation."""
        element_id = f"textBox_{slide_id}"
        requests = [
            {
                "createShape": {
                    "objectId": element_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {
                            "height": {"magnitude": height, "unit": "pt"},
                            "width": {"magnitude": width, "unit": "pt"},
                        },
                        "transform": {
                            "scaleX": 1,
                            "scaleY": 1,
                            "translateX": x,
                            "translateY": y,
                            "unit": "pt",
                        },
                    },
                }
            }
        ]
        self.service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()
        return element_id

    def add_text_to_slide(self, presentation_id: str, page_id: str, text: str) -> None:
        """Adds text to the Google Slides presentation."""
        requests = [{"insertText": {"objectId": page_id, "text": text}}]
        self.service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()

    def replace_text_in_slide(
        self,
        presentation_id: str,
        old_text: str,
        new_text: str,
        match_case: bool = True,
    ) -> None:
        """Replaces text in the Google Slides presentation."""
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": old_text, "matchCase": match_case},
                    "replaceText": new_text,
                }
            }
        ]
        self.service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()

    def get_slide_ids(self, presentation_id: str) -> list:
        """Gets the IDs of the slides in the Google Slides presentation."""
        presentation = self.get_presentation(presentation_id)
        slide_ids = []
        if presentation:
            for slide in presentation.get("slides", []):
                slide_ids.append(slide.get("objectId"))
        return slide_ids

    def get_slide_titles(self, presentation_id: str) -> list:
        """Gets the titles of the slides in the Google Slides presentation."""
        presentation = self.get_presentation(presentation_id)
        titles = []
        if presentation:
            for slide in presentation.get("slides", []):
                for element in slide.get("pageElements", []):
                    if "shape" in element and "text" in element["shape"]:
                        for textElement in element["shape"]["text"]["textElements"]:
                            if "textRun" in textElement:
                                titles.append(textElement["textRun"]["content"])
        return titles

    def delete_slide(self, presentation_id: str, page_id: str) -> None:
        """Deletes a slide from the Google Slides presentation."""
        requests = [{"deleteObject": {"objectId": page_id}}]
        self.service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()

    def search_presentation_by_title(self, title: str) -> list[str]:
        """Searches for Google Slides presentations with the given title."""
        condition = (
            f"name='{title}' and mimeType='application/vnd.google-apps.presentation'"
        )
        presentation_ids = self.drive_service.search_file_by_condition(condition)
        return presentation_ids

    def delete_presentation_by_id(self, presentation_id: str) -> None:
        """Deletes the Google Slides presentation with the given ID."""
        presentation = self.get_presentation(presentation_id)
        logger.info(f"Deleting presentation: {presentation['title']}")
        self.drive_service.delete_file_by_id(presentation_id)

    @evaluation_handler("check_presentation_exists")
    def check_presentation_exists(
        self,
        title: str,
        exists: bool,
        content: str | None = None,
    ) -> None:
        """Checks if the presentation matches the given parameters."""
        presentation_ids = self.search_presentation_by_title(title)
        presentation_exists = False
        if len(presentation_ids) != 0:
            for presentation_id in presentation_ids:
                title_match = self.get_presentation_title(presentation_id) == title
                if content is None:
                    content_match = True
                else:
                    content_match = self.drive_service.compare_file_content(
                        presentation_id, content
                    )
                if title_match and content_match:
                    presentation_exists = True
                    break

        if presentation_exists != exists:
            raise FeedbackException(
                f"The error occured when checking the existence of {title}. "
                f"It should be {exists}."
            )

    @reset_handler("create_presentation")
    def create_presentation(self, title: str) -> None:
        """Creates a Google Slides presentation with the given title."""
        body = {"title": title}
        presentation = self.service.presentations().create(body=body).execute()
        return presentation

    @reset_handler("delete_presentation")
    def delete_presentation(self, title: str, content: str | None = None) -> None:
        """Removes duplicate Google Slides presentations based on their content."""
        presentation_ids = self.search_presentation_by_title(title)
        for presentation_id in presentation_ids:
            if content is None:
                self.delete_presentation_by_id(presentation_id)
            else:
                if self.drive_service.compare_file_content(presentation_id, content):
                    self.delete_presentation_by_id(presentation_id)
