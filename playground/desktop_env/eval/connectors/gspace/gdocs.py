import logging

from playground.desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
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
        self.drive_service = GoogleDriveService()

    def get_document(self, document_id: str) -> dict:
        document = self.service.documents().get(documentId=document_id).execute()
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
        doc = self.service.documents().create(body=body).execute()
        return doc

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
        self.service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()

    def replace_text(self, document_id: str, old_text: str, new_text: str) -> None:
        requests = [
            {
                "replaceAllText": {
                    "containsText": {"text": old_text, "matchCase": "true"},
                    "replaceText": new_text,
                }
            }
        ]
        self.service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()

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
        self.service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()

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
        self.service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()

    def get_recent_documents(self, max_results=1) -> list[str]:
        doc_ids = self.drive_service.get_recent_files(
            "mimeType='application/vnd.google-apps.document'", max_results
        )
        return doc_ids

    def search_doc_by_title(self, title: str) -> list[str]:
        """Search for documents with the given title."""
        condition = (
            f"name='{title}' and mimeType='application/vnd.google-apps.document'"
        )
        doc_ids = self.drive_service.search_file(condition)
        return doc_ids

    def deduplicate_doc(self, doc_ids: list[str], content: str) -> None:
        for doc_id in doc_ids:
            if self.drive_service.compare_file_content(doc_id, content):
                self.delete_doc_by_id(doc_id)

    def delete_doc_by_id(self, doc_id: str) -> None:
        document = self.get_document(doc_id)
        logger.info(f"Deleting document: {document['title']}")
        self.drive_service.delete_file(doc_id)

    def doc_exact_match(self, doc_id: str, title: str, content: str) -> bool:
        """Check if the document matches the given parameters."""
        title_match = self.get_document_title(doc_id) == title
        content_match = self.drive_service.compare_file_content(doc_id, content)
        return title_match and content_match
