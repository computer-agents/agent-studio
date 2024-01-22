import codecs
import io
import logging

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService

logger = logging.getLogger(__name__)


class GoogleDriveService(GoogleService):
    name: str = "google_drive"

    def __init__(self) -> None:
        super().__init__(
            scopes=[
                "https://www.googleapis.com/auth/drive",
            ],
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
            logger.error(err)
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
            logger.error(err)
            return {}

    def list_files(self, folder_id: str | None = None):
        query = f"'{folder_id}' in parents" if folder_id else ""
        try:
            response = self.service.files().list(q=query).execute()
            files = response.get("files", [])
            return files
        except HttpError as err:
            logger.error(err)
            return []

    def delete_file(self, file_id: str) -> None:
        try:
            self.service.files().delete(fileId=file_id).execute()
        except HttpError as err:
            logger.error(err)

    def delete_folder(self, folder_id: str) -> None:
        try:
            self.service.files().delete(fileId=folder_id).execute()
            logger.info(f"Folder with ID {folder_id} has been deleted.")
        except HttpError as err:
            logger.error(err)

    def share_file(self, file_id: str, user_email: str, role: str = "reader") -> None:
        user_permission = {"type": "user", "role": role, "emailAddress": user_email}
        try:
            self.service.permissions().create(
                fileId=file_id, body=user_permission
            ).execute()
        except HttpError as err:
            logger.error(err)

    # Function to search for a file by name in Google Drive
    def search_file(self, file_name):
        results = (
            self.service.files()
            .list(q=f"name='{file_name}'", spaces="drive", fields="files(id)")
            .execute()
        )
        file_ids = [f["id"] for f in results.get("files", [])]
        return file_ids

    # Function to download and compare file content
    def compare_file_content(self, file_id, content):
        # Get file metadata to check MIME type
        file_metadata = (
            self.service.files().get(fileId=file_id, fields="mimeType").execute()
        )
        mime_type = file_metadata["mimeType"]

        # If the file is a Google Docs file, export it in 'text/plain' format
        if mime_type == "application/vnd.google-apps.document":
            request = self.service.files().export_media(
                fileId=file_id, mimeType="text/plain"
            )
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            drive_content = fh.getvalue().decode()
        else:
            # Handle other file types (binary content)
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            drive_content = fh.getvalue().decode()

        drive_content = drive_content.lstrip(codecs.BOM_UTF8.decode("utf-8"))

        return content.strip() == drive_content.strip()

    # Function to search for a folder by name in Google Drive
    def search_folder(self, folder_name):
        results = (
            self.service.files()
            .list(
                q=f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}'",  # noqa: E501
                spaces="drive",
                fields="files(id, name)",
            )
            .execute()
        )
        folder_ids = [f["id"] for f in results.get("files", [])]
        return folder_ids

    def get_recent_documents(self, max_results=1):
        try:
            # Query for recent Google Docs documents
            results = (
                self.service.files()
                .list(
                    pageSize=max_results,
                    fields="files(id, name, createdTime)",
                    orderBy="createdTime desc",
                    q="mimeType='application/vnd.google-apps.document'",
                )
                .execute()
            )

            items = results.get("files", [])
            if not items:
                logger.warn("No documents found.")
            else:
                return items
        except HttpError as err:
            logger.error(err)
            return []
