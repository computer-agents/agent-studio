import logging

from playground.desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService

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
        spreadsheet_body = {"properties": {"title": title}}
        spreadsheet = (
            self.service.spreadsheets().create(body=spreadsheet_body).execute()
        )
        return spreadsheet

    def get_spreadsheet(self, spreadsheet_id: str) -> dict:
        spreadsheet = (
            self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        return spreadsheet

    def get_spreadsheet_title(self, spreadsheet_id: str) -> str:
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        if spreadsheet:
            return spreadsheet.get("properties", {}).get("title", "")
        return ""

    def read_range(self, spreadsheet_id: str, range_name: str) -> list:
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        return result.get("values", [])

    def write_range(self, spreadsheet_id: str, range_name: str, values: list) -> None:
        body = {"values": values}
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

    def append_values(self, spreadsheet_id: str, range_name: str, values: list) -> None:
        body = {"values": values}
        self.service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()

    def clear_range(self, spreadsheet_id: str, range_name: str) -> None:
        self.service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name, body={}
        ).execute()

    def get_recent_spreadsheets(self, max_results=1) -> list[str]:
        """Retrieve the most recent Google Sheets spreadsheets."""
        spreadsheet_ids = self.drive_service.get_recent_files(
            "mimeType='application/vnd.google-apps.spreadsheet'", max_results
        )
        return spreadsheet_ids

    def search_spreadsheet_by_title(self, title: str) -> list[str]:
        """Search for Google Sheets spreadsheets with the given title."""
        condition = (
            f"name='{title}' and mimeType='application/vnd.google-apps.spreadsheet'"
        )
        spreadsheet_ids = self.drive_service.search_file(condition)
        return spreadsheet_ids

    def deduplicate_spreadsheet(
        self, spreadsheet_ids: list[str], content: str | None
    ) -> None:
        """Remove duplicate Google Sheets spreadsheets based on their content."""
        for spreadsheet_id in spreadsheet_ids:
            if content is None:
                self.delete_spreadsheet_by_id(spreadsheet_id)
            else:
                if self.drive_service.compare_file_content(spreadsheet_id, content):
                    self.delete_spreadsheet_by_id(spreadsheet_id)

    def delete_spreadsheet_by_id(self, spreadsheet_id: str) -> None:
        spreadsheet = self.get_spreadsheet(spreadsheet_id)
        logger.info(f"Deleting spreadsheet: {spreadsheet['properties']['title']}")
        self.drive_service.delete_file(spreadsheet_id)

    def spreadsheet_exact_match(
        self, spreadsheet_id: str, title: str, content: str | None
    ) -> bool:
        """Check if the Google Sheets spreadsheet matches the given parameters."""
        title_match = self.get_spreadsheet_title(spreadsheet_id) == title
        if content is None:
            content_match = True
        else:
            content_match = self.drive_service.compare_file_content(
                spreadsheet_id, content
            )
        return title_match and content_match
