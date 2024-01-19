import logging

from googleapiclient.errors import HttpError

from playground.desktop_env.eval.connectors.gspace.gservice import GoogleService

logger = logging.getLogger(__name__)


class GoogleDocsService(GoogleService):
    def __init__(self) -> None:
        super().__init__(
            scopes=[
                "https://www.googleapis.com/auth/documents",
            ],
            service_name="docs",
            service_version="v1",
        )

    def get_document(self, document_id: str) -> dict:
        try:
            document = self.service.documents().get(documentId=document_id).execute()
        except HttpError as err:
            logger.error(err)
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
            logger.error(err)
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
            logger.error(err)

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
            logger.error(err)

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
            logger.error(err)

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
            logger.error(err)
