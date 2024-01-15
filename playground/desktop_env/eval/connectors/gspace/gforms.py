from typing import Any

from googleapiclient.errors import HttpError

from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService


class GoogleFormsService(GoogleService):
    name: str = "google_forms"

    def __init__(self, credential_path: str) -> None:
        super().__init__(
            scopes=["https://www.googleapis.com/auth/forms.body"],
            credential_path=credential_path,
            service_name="forms",
            service_version="v1",
        )

    def create_form(self, form_body: dict[str, Any]) -> dict:
        try:
            form = self.service.forms().create(body=form_body).execute()
            return form
        except HttpError as err:
            print(err)
            return {}

    def add_question(self, form_id: str, question: dict[str, Any], index: int) -> None:
        try:
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
        except HttpError as err:
            print(f"An error occurred: {err}")

    def get_form(self, form_id: str) -> dict:
        try:
            form = self.service.forms().get(formId=form_id).execute()
            return form
        except HttpError as err:
            print(err)
            return {}
