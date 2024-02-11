import logging

from playground.env.desktop_env.eval.connectors.gservice import GoogleService
from playground.env.desktop_env.eval.evaluator import Evaluator, FeedBackException
from playground.env.desktop_env.eval.google_evaluators.drive_evaluator import (
    GoogleDriveService,
)
from playground.utils.human_utils import confirm_action

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

    def create_document(self, title: str, content: str | None = None) -> dict:
        """Creates a document with the given title and content."""
        body = {"title": title}
        doc = self.service.documents().create(body=body).execute()
        if content:
            self.append_text(doc["documentId"], content)
        return doc

    def get_document(self, document_id: str) -> dict:
        """Gets a document by its ID."""
        document = self.service.documents().get(documentId=document_id).execute()
        return document

    def get_text_at_index(self, document, index):
        """Gets the text at the given index in the document."""
        for element in document["body"]["content"]:
            if "startIndex" in element and "endIndex" in element:
                if element["startIndex"] <= index < element["endIndex"]:
                    # Assuming the element contains text
                    if "textRun" in element["paragraph"]["elements"][0]:
                        return element["paragraph"]["elements"][0]["textRun"]["content"]
        return None

    def append_text(self, document_id: str, text: str) -> None:
        """Appends text to the document."""
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
        """Replaces text in the document."""
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
        """Gets the title of the document."""
        document = self.get_document(document_id)
        if document:
            return document.get("title", "")
        return ""

    @confirm_action
    def delete_text(self, document_id: str, start_index: int, end_index: int) -> None:
        """Deletes text in the document."""
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
        """Inserts a table at the given index in the document."""
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

    def search_doc_by_title(self, title: str) -> list[str]:
        """Searches for documents with the given title."""
        condition = (
            f"name='{title}' and mimeType='application/vnd.google-apps.document'"
        )
        doc_ids = self.drive_service.search_file_by_condition(condition)
        return doc_ids

    def delete_doc_by_id(self, doc_id: str) -> None:
        """Deletes a document by its ID."""
        document = self.get_document(doc_id)
        logger.info(f"Deleting document: {document['title']}")
        self.drive_service.delete_file_by_id(doc_id)

    def delete_document(self, title: str, content: str) -> None:
        """Deletes a document with the given title and content."""
        doc_ids = self.search_doc_by_title(title)
        if len(doc_ids) != 0:
            for doc_id in doc_ids:
                if self.drive_service.compare_file_content(doc_id, content):
                    self.delete_doc_by_id(doc_id)

    def check_doc_exists(
        self, title: str, exists: bool, content: str | None = None
    ) -> None:
        """Checks if the document matches the given parameters."""
        doc_ids = self.search_doc_by_title(title)
        doc_exists = False
        if len(doc_ids) != 0:
            for doc_id in doc_ids:
                title_match = self.get_document_title(doc_id) == title
                if content is None:
                    content_match = True
                else:
                    content_match = self.drive_service.compare_file_content(
                        doc_id, content
                    )
                if title_match and content_match:
                    doc_exists = True
                    break
        if doc_exists != exists:
            raise FeedBackException(
                f"The error occured when checking the existence of {title}. "
                f"It should be {exists}."
            )


class GoogleDocsEvaluator(Evaluator):
    name: str = "google_docs"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )
        self.service = GoogleDocsService()
        self.evaluation_handlers = {
            "check_doc_exists": self.service.check_doc_exists,
        }
        self.reset_handlers = {
            "create_document": self.service.create_document,
            "delete_document": self.service.delete_document,
        }
