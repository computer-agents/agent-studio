from typing import Any

from desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService


def test_gdrive_connector() -> None:
    credential_path = "config/token.json"
    drive_service = GoogleDriveService(credential_path)

    # Create a folder in Google Drive
    folder = drive_service.create_folder(folder_name="TestFolder")
    folder_id: Any = folder.get("id")
    print(f"Created folder with ID: {folder_id}")

    # Upload a file to the created folder
    file = drive_service.upload_file(
        file_name="TestFile.txt",
        file_path="tmp/test.txt",
        mime_type="text/plain",
        folder_id=folder_id,
    )
    file_id: Any = file.get("id")
    print(f"Uploaded file with ID: {file_id}")

    # List files in the folder
    files = drive_service.list_files(folder_id=folder_id)
    print("Files in folder:")
    for f in files:
        print(f" - {f.get('name')} (ID: {f.get('id')})")

    # Download the uploaded file
    drive_service.download_file(file_id, "tmp/testfile_downloaded.txt")
    print("Downloaded the file.")

    # Delete the folder
    drive_service.delete_folder(folder_id=folder_id)
    print("Folder deleted.")

    # # Share the file with another user (not tested)
    # drive_service.share_file(file_id, 'user@example.com', 'reader')
    # print('Shared the file.')
