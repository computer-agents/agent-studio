import logging

from playground.env.desktop_env.eval.connectors.gservice import GoogleService
from playground.env.desktop_env.eval.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from playground.env.desktop_env.eval.google_evaluators.drive_evaluator import (
    GoogleDriveService,
)

logger = logging.getLogger(__name__)


class GoogleSheetsService(GoogleService):
    def __init__(self) -> None:
        super().__init__(
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
            service_name="sheets",
            service_version="v4",
        )
        self.drive_service = GoogleDriveService()

    def create_spreadsheet(self, title: str) -> dict:
        """Creates a Google Sheets spreadsheet with the given title."""
        spreadsheet_body = {"properties": {"title": title}}
        spreadsheet = (
            self.service.spreadsheets().create(body=spreadsheet_body).execute()
        )
        return spreadsheet

    def get_spreadsheet(self, spreadsheet_id: str) -> dict:
        """Gets the Google Sheets spreadsheet by its ID."""
        spreadsheet = (
            self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        return spreadsheet

    def get_spreadsheet_title(self, spreadsheet_id: str) -> str:
        """Gets the title of the Google Sheets spreadsheet."""
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        if spreadsheet:
            return spreadsheet.get("properties", {}).get("title", "")
        return ""

    def read_range(self, spreadsheet_id: str, range_name: str) -> list:
        """Reads values from the Google Sheets spreadsheet."""
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    def write_range(self, spreadsheet_id: str, range_name: str, values: list) -> None:
        """Writes values to the Google Sheets spreadsheet."""
        body = {"values": values}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

    def append_values(self, spreadsheet_id: str, range_name: str, values: list) -> None:
        """Appends values to the Google Sheets spreadsheet."""
        body = {"values": values}
        self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

    def clear_range(self, spreadsheet_id: str, range_name: str) -> None:
        """Clears the range in the Google Sheets spreadsheet."""
        self.service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name, body={}
        ).execute()

    def search_spreadsheet_by_title(self, title: str) -> list[str]:
        """Searches for Google Sheets spreadsheets with the given title."""
        condition = (
            f"name='{title}' and mimeType='application/vnd.google-apps.spreadsheet'"
        )
        spreadsheet_ids = self.drive_service.search_file_by_condition(condition)
        return spreadsheet_ids

    def delete_spreadsheet(self, title: str, content: str | None = None) -> None:
        """Removes duplicate Google Sheets spreadsheets based on their content."""
        spreadsheet_ids = self.search_spreadsheet_by_title(title)
        for spreadsheet_id in spreadsheet_ids:
            if content is None:
                self.delete_spreadsheet_by_id(spreadsheet_id)
            else:
                if self.drive_service.compare_file_content(spreadsheet_id, content):
                    self.delete_spreadsheet_by_id(spreadsheet_id)

    def delete_spreadsheet_by_id(self, spreadsheet_id: str) -> None:
        """Deletes the Google Sheets spreadsheet with the given ID."""
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        logger.info(f"Deleting spreadsheet: {spreadsheet['properties']['title']}")
        self.drive_service.delete_file_by_id(spreadsheet_id)

    def check_spreadsheet_exists(
        self, title: str, exists: bool, content: str | None = None
    ) -> None:
        """Checks if the spreadsheet matches the given parameters."""
        spreadsheet_ids = self.search_spreadsheet_by_title(title)
        print("ss:", spreadsheet_ids)
        spreadsheet_exists = False
        if len(spreadsheet_ids) != 0:
            for spreadsheet_id in spreadsheet_ids:
                title_match = self.get_spreadsheet_title(spreadsheet_id) == title
                if content is None:
                    content_match = True
                else:
                    content_match = self.drive_service.compare_file_content(
                        spreadsheet_id, content
                    )
                if title_match and content_match:
                    spreadsheet_exists = True
                    break

        if spreadsheet_exists != exists:
            raise FeedbackException(
                f"The error occured when checking the existence of {title}. "
                f"It should be {exists}."
            )


class GoogleSheetsEvaluator(Evaluator):
    name: str = "google_sheets"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = GoogleSheetsService()

    @evaluation_handler("check_spreadsheet_exists")
    def check_spreadsheet_exists(
        self,
        title: str,
        exists: bool,
        content: str | None = None,
    ) -> None:
        self.service.check_spreadsheet_exists(title, exists, content)

    @reset_handler("create_spreadsheet")
    def create_spreadsheet(self, title: str) -> None:
        self.service.create_spreadsheet(title)

    @reset_handler("delete_spreadsheet")
    def delete_spreadsheet(self, title: str, content: str | None = None) -> None:
        self.service.delete_spreadsheet(title, content)
