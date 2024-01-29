import logging
from typing import Any

from playground.desktop_env.eval.connectors.gservice import GoogleService

logger = logging.getLogger(__name__)


class GoogleFormsService(GoogleService):
    name: str = "google_forms"

    def __init__(self) -> None:
        super().__init__(
            scopes=["https://www.googleapis.com/auth/forms.body"],
            service_name="forms",
            service_version="v1",
        )

    def create_form(self, form_body: dict[str, Any]) -> dict:
        form = self.service.forms().create(body=form_body).execute()
        return form

    def add_question(self, form_id: str, question: dict[str, Any], index: int) -> None:
        body = {
            "requests": [
                {
                    "createItem": {
                        "item": question,
                        "location": {"index": index},
                    }
                }
            ]
        }
        self.service.forms().batchUpdate(formId=form_id, body=body).execute()

    def get_form(self, form_id: str) -> dict:
        form = self.service.forms().get(formId=form_id).execute()
        return form
