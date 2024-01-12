from googleapiclient.errors import HttpError

from desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
from desktop_env.eval.connectors.gspace.gservice import GoogleService


class GoogleDocsService(GoogleService):
    def __init__(self, token_path: str) -> None:
        super().__init__(
            token_path=token_path,
            service_name="docs",
            service_version="v1",
        )
        self.drive_service = GoogleDriveService(token_path)

    def get_document(self, document_id: str) -> dict:
        try:
            document = self.service.documents().get(documentId=document_id).execute()
        except HttpError as err:
            print(err)
            return {}
        return document

    def get_text_at_index(self, document, index):
        for element in document["body"]["content"]:
            if "startIndex" in element and "endIndex" in element:
                if element["startIndex"] <= index < element["endIndex"]:
                    # Assuming the element contains text
                    if "textRun" in element["paragraph"]["elements"][0]:
                        return element["paragraph"]["elements"][0]["textRun"]["content"]
        return None

    def create_document(self, title: str) -> dict:
        body = {"title": title}
        try:
            doc = self.service.documents().create(body=body).execute()
            return doc
        except HttpError as err:
            print(err)
            return {}

    def append_text(self, document_id: str, text: str) -> None:
        requests = [
            {
                "insertText": {
                    "location": {
                        "index": 1,
                    },
                    "text": text,
                }
            }
        ]
        try:
            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

    def replace_text(self, document_id: str, old_text: str, new_text: str) -> None:
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": old_text, "matchCase": "true"},
                    "replaceText": new_text,
                }
            }
        ]
        try:
            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

    def get_document_title(self, document_id: str) -> str:
        document = self.get_document(document_id)
        if document:
            return document.get("title", "")
        return ""

    def delete_text(self, document_id: str, start_index: int, end_index: int) -> None:
        requests = [
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": start_index,
                        "endIndex": end_index,
                    }
                }
            }
        ]
        try:
            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

    def insert_table(
        self, document_id: str, rows: int, columns: int, index: int = 1
    ) -> None:
        requests = [
            {
                "insertTable": {
                    "rows": rows,
                    "columns": columns,
                    "location": {"index": index},
                }
            }
        ]
        try:
            self.service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()
        except HttpError as err:
            print(err)

    def delete_document(self, file_id: str) -> None:
        try:
            self.drive_service.delete_file(file_id=file_id)
        except HttpError as err:
            print(err)
