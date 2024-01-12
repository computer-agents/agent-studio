from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from desktop_env.eval.connectors.gspace.gservice import GoogleService


class GoogleDriveService(GoogleService):
    name: str = "google_drive"

    def __init__(self, credential_path: str) -> None:
        super().__init__(
            scopes=[
                "https://www.googleapis.com/auth/drive",
            ],
            credential_path=credential_path,
            service_name="drive",
            service_version="v3",
        )

    def upload_file(
        self,
        file_name: str,
        file_path: str,
        mime_type: str,
        folder_id: str | None = None,
    ) -> dict:
        file_metadata = {"name": file_name, "parents": [folder_id] if folder_id else []}
        media = MediaFileUpload(file_path, mimetype=mime_type)
        try:
            file = (
                self.service.files()
                .create(body=file_metadata, media_body=media, fields="id")
                .execute()
            )
            return file
        except HttpError as err:
            print(err)
            return {}

    def download_file(self, file_id: str, output_file: str) -> None:
        request = self.service.files().get_media(fileId=file_id)
        with open(output_file, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

    def create_folder(self, folder_name: str) -> dict:
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        try:
            folder = (
                self.service.files().create(body=file_metadata, fields="id").execute()
            )
            return folder
        except HttpError as err:
            print(err)
            return {}

    def list_files(self, folder_id: str | None = None):
        query = f"'{folder_id}' in parents" if folder_id else ""
        try:
            response = self.service.files().list(q=query).execute()
            files = response.get("files", [])
            return files
        except HttpError as err:
            print(err)
            return []

    def delete_file(self, file_id: str) -> None:
        try:
            self.service.files().delete(fileId=file_id).execute()
        except HttpError as err:
            print(err)

    def delete_folder(self, folder_id: str) -> None:
        try:
            self.service.files().delete(fileId=folder_id).execute()
            print(f"Folder with ID {folder_id} has been deleted.")
        except HttpError as err:
            print(err)

    def share_file(self, file_id: str, user_email: str, role: str = "reader") -> None:
        user_permission = {"type": "user", "role": role, "emailAddress": user_email}
        try:
            self.service.permissions().create(
                fileId=file_id, body=user_permission
            ).execute()
        except HttpError as err:
            print(err)
