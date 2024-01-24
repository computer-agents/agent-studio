import logging

from playground.desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService

logger = logging.getLogger(__name__)


class GoogleSlidesService(GoogleService):
    name: str = "google_slides"

    def __init__(self) -> None:
        super().__init__(
            scopes=["https://www.googleapis.com/auth/presentations"],
            service_name="slides",
            service_version="v1",
        )
        self.drive_service = GoogleDriveService()

    def create_presentation(self, title: str) -> dict:
        body = {"title": title}
        presentation = self.service.presentations().create(body=body).execute()
        return presentation

    def get_presentation(self, presentation_id: str) -> dict:
        presentation = (
            self.service.presentations().get(presentationId=presentation_id).execute()
        )
        return presentation

    def get_presentation_title(self, presentation_id: str) -> str:
        presentation = self.get_presentation(presentation_id)
        if presentation:
            return presentation.get("title", "")
        return ""

    def add_slide(self, presentation_id: str, page_id: str | None = None) -> None:
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
        presentation = self.get_presentation(presentation_id)
        slide_ids = []
        if presentation:
            for slide in presentation.get("slides", []):
                slide_ids.append(slide.get("objectId"))
        return slide_ids

    def get_slide_titles(self, presentation_id: str) -> list:
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
        requests = [{"deleteObject": {"objectId": page_id}}]
        self.service.presentations().batchUpdate(
            presentationId=presentation_id, body={"requests": requests}
        ).execute()

    def get_recent_presentations(self, max_results=1) -> list[str]:
        """Retrieve the most recent Google Slides presentations."""
        presentation_ids = self.drive_service.get_recent_files(
            "mimeType='application/vnd.google-apps.presentation'", max_results
        )
        return presentation_ids

    def search_presentation_by_title(self, title: str) -> list[str]:
        """Search for Google Slides presentations with the given title."""
        condition = (
            f"name='{title}' and mimeType='application/vnd.google-apps.presentation'"
        )
        presentation_ids = self.drive_service.search_file(condition)
        return presentation_ids

    def deduplicate_presentation(
        self, presentation_ids: list[str], content: str | None
    ) -> None:
        """Remove duplicate Google Slides presentations based on their content."""
        for presentation_id in presentation_ids:
            if content is None:
                self.delete_presentation_by_id(presentation_id)
            else:
                if self.drive_service.compare_file_content(presentation_id, content):
                    self.delete_presentation_by_id(presentation_id)

    def delete_presentation_by_id(self, presentation_id: str) -> None:
        presentation = self.get_presentation(presentation_id)
        logger.info(f"Deleting presentation: {presentation['title']}")
        self.drive_service.delete_file(presentation_id)

    def presentation_exact_match(
        self, presentation_id: str, title: str, content: str | None
    ) -> bool:
        """Check if the Google Slides presentation matches the given parameters."""
        title_match = self.get_presentation_title(presentation_id) == title
        if content is None:
            content_match = True
        else:
            content_match = self.drive_service.compare_file_content(
                presentation_id, content
            )
        return title_match and content_match
