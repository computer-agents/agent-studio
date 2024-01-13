from typing import Any

from desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
from desktop_env.eval.connectors.gspace.gsheets import GoogleSheetsService


def test_gsheets_connector() -> None:
    credentials_path = "config/credentials.json"
    sheets_service = GoogleSheetsService(credentials_path)

    # Create a new Google Sheet
    new_sheet = sheets_service.create_sheet("Test Sheet")
    if not new_sheet:
        print("Failed to create a new Google Sheet.")
        return

    spreadsheet_id: Any = new_sheet["spreadsheetId"]
    print(f"Created new Google Sheet with ID: {spreadsheet_id}")

    # Write data to the Google Sheet
    range_name = "Sheet1!A1:B2"
    values = [["Name", "Age"], ["Alice", 30]]
    sheets_service.write_range(spreadsheet_id, range_name, values)
    print("Data written to sheet.")

    # Read data from the Google Sheet
    data = sheets_service.read_range(spreadsheet_id, range_name)
    print("Data read from sheet:")
    print(data)

    # Append data to the Google Sheet
    append_range = "Sheet1!A3"
    append_values = [["Bob", 25]]
    sheets_service.append_values(spreadsheet_id, append_range, append_values)
    print("Data appended to sheet.")

    # Clear data from a range in the Google Sheet
    clear_range = "Sheet1!B2:B3"
    sheets_service.clear_range(spreadsheet_id, clear_range)
    print("Data cleared from sheet.")

    # Delete the spreadsheet
    drive_service = GoogleDriveService(credentials_path)
    drive_service.delete_file(file_id=spreadsheet_id)
    print(f"Deleted sheet with ID: {spreadsheet_id}")
