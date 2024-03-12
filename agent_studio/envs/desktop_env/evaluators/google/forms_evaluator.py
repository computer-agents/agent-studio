import logging
from typing import Any

from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.envs.desktop_env.evaluators.google.drive_evaluator import (
    GoogleDriveService,
)
from agent_studio.envs.desktop_env.evaluators.google.gservice import GoogleService

config = Config()
logger = logging.getLogger(__name__)


def form_match(form_to_match: dict[str, Any], ref_form: dict[str, Any]) -> bool:
    """Checks if the form_to_match matches the ref_form."""
    result = True
    # if "body" in ref_form:
    #     result &= (
    #         form_to_match["body"].strip() == ref_form["body"].strip()
    #     )
    for key in ["title"]:
        if ref_form.get(key, None) is not None:
            result &= form_to_match[key] == ref_form[key]

    return result


class GoogleFormsService(GoogleService):
    def __init__(self) -> None:
        super().__init__(
            scopes=[
                "https://www.googleapis.com/auth/forms",
                "https://www.googleapis.com/auth/forms.body",
            ],
            service_name="forms",
            service_version="v1",
        )
        self.drive_service = GoogleDriveService()

    def create_form(self, title: str, description: str | None = None) -> dict:
        """Creates a form with the given title and description."""
        form_body = {"info": {"title": title}}
        # if description:
        #     form_body["description"] = description
        form = self.service.forms().create(body=form_body).execute()
        form_id = form.get("formId")
        self.drive_service.rename_file(form_id, title)
        return form

    def get_form(self, form_id: str) -> dict:
        """Gets a form by its ID."""
        form = self.service.forms().get(formId=form_id).execute()
        return {
            "title": form["info"]["title"],
        }

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

    def search_form_by_title(self, title: str) -> list[str]:
        """Searches for forms with the given title."""
        condition = f"name='{title}' and mimeType='application/vnd.google-apps.form'"
        form_ids = self.drive_service.search_file_by_condition(condition)
        return form_ids

    def delete_form_by_id(self, form_id: str) -> None:
        """Deletes a form by its ID."""
        form = self.get_form(form_id)
        logger.info(f"Deleting form: {form['title']}")
        self.drive_service.delete_file_by_id(form_id)

    def delete_form(self, form_info: dict[str, Any]) -> None:
        """Deletes a form with the given title and description."""
        form_ids = self.search_form_by_title(form_info["title"])
        if len(form_ids) != 0:
            for form_id in form_ids:
                if form_match(self.get_form(form_id), form_info):
                    self.delete_form_by_id(form_id)

    def check_form_exists(self, form_info: dict[str, Any], exists: bool) -> None:
        """Checks if the form matches the given parameters."""
        form_ids = self.search_form_by_title(form_info["title"])
        form_exists = False
        if len(form_ids) != 0:
            for form_id in form_ids:
                form = self.get_form(form_id)
                if form_match(form, form_info):
                    form_exists = True
                    break
        if form_exists != exists:
            raise FeedbackException(
                f"The error occurred when checking the existence of {form_info}. "
                f"It should be {exists}."
            )


class GoogleFormsEvaluator(Evaluator):
    name: str = "google_forms"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = GoogleFormsService()

    @evaluation_handler("check_form_exists")
    def check_form_exists(
        self,
        form_info: dict[str, Any],
        exists: bool,
    ) -> None:
        self.service.check_form_exists(form_info, exists)

    @reset_handler("create_form")
    def create_form(
        self,
        title: str,
        description: str | None = None,
    ) -> None:
        self.service.create_form(title, description)

    @reset_handler("delete_form")
    def delete_form(
        self,
        form_info: dict[str, Any],
    ) -> None:
        self.service.delete_form(form_info)
