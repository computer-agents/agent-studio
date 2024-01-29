import codecs
import io
import logging

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from playground.desktop_env.eval.connectors.gservice import GoogleService
from playground.desktop_env.eval.evaluator import Evaluator
from playground.desktop_env.eval.google_evaluators.utils import confirm_action

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
        name: str,
        path: str,
        mime_type: str,
        folder_id: str | None = None,
    ) -> dict:
        """Uploads a file to Google Drive."""
        file_metadata = {"name": name, "parents": [folder_id] if folder_id else []}
        media = MediaFileUpload(path, mimetype=mime_type)
        file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file

    def download_file(self, file_id: str, output_file: str) -> None:
        """Downloads a file from Google Drive."""
        request = self.service.files().get_media(fileId=file_id)
        with open(output_file, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

    def create_folder(
        self, folder_name: str, file_list: list[dict] | None = None
    ) -> dict:
        """Creates a folder in Google Drive."""
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        folder = self.service.files().create(body=file_metadata, fields="id").execute()
        if file_list:
            for file in file_list:
                self.upload_file(
                    name=file["name"],
                    path=file["path"],
                    mime_type=file["mime_type"],
                    folder_id=folder["id"],
                )
        return folder

    def list_files(self, folder_id: str | None = None):
        """Lists all files in Google Drive."""
        query = f"'{folder_id}' in parents" if folder_id else ""
        response = self.service.files().list(q=query).execute()
        files = response.get("files", [])
        return files

    def get_filename(self, file_id: str) -> str:
        """Gets the file name by ID."""
        file_metadata = self.service.files().get(fileId=file_id).execute()
        return file_metadata["name"]

    def search_file_by_condition(self, condition: str) -> list[str]:
        """Searches for a file in Google Drive."""
        results = (
            self.service.files()
            .list(q=condition, spaces="drive", fields="files(id)")
            .execute()
        )
        file_ids = [f["id"] for f in results.get("files", [])]
        return file_ids

    def search_file(self, file_name: str) -> list[str]:
        """Searches for a file by name in Google Drive."""
        condition = f"name='{file_name}'"
        return self.search_file_by_condition(condition)

    def search_folder(self, folder_name):
        """Searches for a folder in Google Drive."""
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

    def get_recent_files(self, condition: str, max_results: int = 1) -> list[str]:
        results = (
            self.service.files()
            .list(
                pageSize=max_results,
                fields="files(id, name, createdTime)",
                orderBy="createdTime desc",
                q=condition,
            )
            .execute()
        )

        file_ids = [f["id"] for f in results.get("files", [])]
        return file_ids

    @confirm_action
    def delete_file_by_id(self, file_id: str) -> None:
        """Deletes a file from Google Drive."""
        self.service.files().delete(fileId=file_id).execute()
        logger.info(f"File with ID {file_id} has been deleted.")

    @confirm_action
    def delete_folder_by_id(self, folder_id: str) -> None:
        """Deletes a folder from Google Drive."""
        self.service.files().delete(fileId=folder_id).execute()
        logger.info(f"Folder with ID {folder_id} has been deleted.")

    def delete_file(self, file_name: str) -> None:
        """Deletes a file from Google Drive with name."""
        file_ids = self.search_file(file_name)
        for file_id in file_ids:
            file_name = self.get_filename(file_id)
            logger.info(f"Deleting file with name {file_name}")
            self.delete_file_by_id(file_id)

    def delete_folder(self, folder_name: str) -> None:
        """Deletes a folder from Google Drive with name."""
        folder_ids = self.search_folder(folder_name)
        for folder_id in folder_ids:
            folder_name = self.get_filename(folder_id)
            logger.info(f"Deleting folder with name {folder_name}")
            self.delete_folder_by_id(folder_id)

    def check_file_exists(
        self, file_name: str, exists: bool, content: str | None = None
    ) -> bool:
        """Checks if a file exists in Google Drive."""
        file_ids = self.search_file(file_name)
        file_exists = len(file_ids) > 0
        if content is not None:
            file_exists &= self.compare_file_content(file_ids[0], content)

        return file_exists == exists

    def check_folder_exists(
        self, folder_name: str, exists: bool, file_list: list[dict] | None = None
    ) -> bool:
        """Checks if a folder exists in Google Drive."""
        folder_ids = self.search_folder(folder_name)
        folder_exists = len(folder_ids) > 0
        if file_list:
            files = self.list_files(folder_ids[0])
            folder_exists &= len(files) == len(file_list) and all(
                [f1["name"] == f2["name"] for f1, f2 in zip(file_list, files)]
            )
        return folder_exists == exists

    def compare_file_content(self, file_id: str, content: str) -> bool:
        """Compares the content of a file in Google Drive with the given content."""
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

    def share_file(self, file_id: str, user_email: str, role: str = "reader") -> None:
        """Shares a file with a user."""
        user_permission = {"type": "user", "role": role, "emailAddress": user_email}
        self.service.permissions().create(
            fileId=file_id, body=user_permission
        ).execute()


class GoogleDriveEvaluator(Evaluator):
    name: str = "google_drive"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = GoogleDriveService()
        self.evaluation_handlers = {
            "check_file_exists": self.service.check_file_exists,
            "check_folder_exists": self.service.check_folder_exists,
        }
        self.reset_handlers = {
            "create_folder": self.service.create_folder,
            "upload_file": self.service.upload_file,
            "delete_file": self.service.delete_file,
            "delete_folder": self.service.delete_folder,
        }
        self.feedback_handlers = {
            "check_file_exists": lambda file_name, exists: f"The error occured when checking the existence of {file_name}. It should be {exists}.",  # noqa: E501
            "check_folder_exists": lambda folder_name, exists: f"The error occured when checking the existence of {folder_name}. It should be {exists}.",  # noqa: E501
        }
