from googleapiclient.errors import HttpError

from desktop_env.eval.connectors.gspace.gservice import GoogleService


class GoogleSlidesService(GoogleService):
    def __init__(self, credential_path: str) -> None:
        super().__init__(
            scopes=["https://www.googleapis.com/auth/presentations"],
            credential_path=credential_path,
            service_name="slides",
            service_version="v1",
        )

    def create_presentation(self, title: str) -> dict:
        body = {"title": title}
        try:
            presentation = self.service.presentations().create(body=body).execute()
            return presentation
        except HttpError as err:
            print(err)
            return {}

    def get_presentation(self, presentation_id: str) -> dict:
        try:
            presentation = (
                self.service.presentations()
                .get(presentationId=presentation_id)
                .execute()
            )
            return presentation
        except HttpError as err:
            print(err)
            return {}

    def add_slide(self, presentation_id: str, page_id: str | None = None) -> None:
        requests = [
            {
                "createSlide": {
                    "objectId": page_id,
                }
            }
        ]
        try:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

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
        try:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
            return element_id
        except HttpError as err:
            print(err)
            return None

    def add_text_to_slide(self, presentation_id: str, page_id: str, text: str) -> None:
        requests = [{"insertText": {"objectId": page_id, "text": text}}]
        try:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

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
        try:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

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
        try:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)
