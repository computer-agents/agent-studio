from googleapiclient.errors import HttpError

from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService
from playground.utils.logger import Logger

logger = Logger()


class GoogleSheetsService(GoogleService):
    def __init__(self) -> None:
        super().__init__(
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
            service_name="sheets",
            service_version="v4",
        )

    def create_sheet(self, title: str) -> dict:
        spreadsheet_body = {"properties": {"title": title}}
        try:
            spreadsheet = (
                self.service.spreadsheets().create(body=spreadsheet_body).execute()
            )
            return spreadsheet
        except HttpError as err:
            logger.error(err)
            return {}

    def read_range(self, spreadsheet_id: str, range_name: str) -> list:
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            return result.get("values", [])
        except HttpError as err:
            logger.error(err)
            return []

    def write_range(self, spreadsheet_id: str, range_name: str, values: list) -> None:
        body = {"values": values}
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
        except HttpError as err:
            logger.error(err)

    def append_values(self, spreadsheet_id: str, range_name: str, values: list) -> None:
        body = {"values": values}
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
        except HttpError as err:
            logger.error(err)

    def clear_range(self, spreadsheet_id: str, range_name: str) -> None:
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=range_name, body={}
            ).execute()
        except HttpError as err:
            logger.error(err)
