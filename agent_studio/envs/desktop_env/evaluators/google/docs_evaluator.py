import logging

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.envs.desktop_env.evaluators.google.drive_evaluator import (
    GoogleDriveService,
)
from agent_studio.envs.desktop_env.evaluators.google.gservice import GoogleService
from agent_studio.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)


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
        self.service = GoogleService(
            scopes=[
                "https://www.googleapis.com/auth/documents",
            ],
            service_name="docs",
            service_version="v1",
        ).service
        self.drive_service = GoogleDriveService()

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
        logger.debug(f"Deleting document: {document['title']}")
        confirm_action(f"Deleting document: {document['title']}")(
            self.drive_service.delete_file_by_id
        )(doc_id)

    def find_text_format(self, document, text) -> dict | None:
        """Finds the formatting of the given text in the document."""

        namedStyles = document.get("namedStyles").get("styles")
        defaultStyle = {}
        for style in namedStyles:
            if style.get("namedStyleType") == "NORMAL_TEXT":
                textStyle = style.get("textStyle")
                defaultStyle["font"] = textStyle.get("weightedFontFamily", {}).get(
                    "fontFamily"
                )
                defaultStyle["fontSize"] = textStyle.get("fontSize", {}).get(
                    "magnitude"
                )
                defaultStyle["color"] = (
                    textStyle.get("foregroundColor", {})
                    .get("color", {})
                    .get("rgbColor", {})
                )
                break

        # Iterate through the document elements to find the search text
        for element in document.get("body").get("content"):
            if "paragraph" in element:
                for parElement in element.get("paragraph").get("elements"):
                    text_run = parElement.get("textRun")
                    if text_run and text in text_run.get("content"):
                        textStyle = text_run.get("textStyle")
                        return {
                            "text": text_run.get("content").strip(),
                            "font": textStyle.get("weightedFontFamily", {}).get(
                                "fontFamily", defaultStyle["font"]
                            ),
                            "size": textStyle.get("fontSize", {}).get(
                                "magnitude", defaultStyle["fontSize"]
                            ),
                        }

        return None

    def find_hyperlink(
        self, document: dict, search_text: str, expected_url: str
    ) -> bool:
        """
        Searches for a hyperlink in the document with the specified text and URL.

        Args:
            document (dict): The document object.
            search_text (str): The text of the hyperlink to search for.
            expected_url (str): The expected URL of the hyperlink.

        Returns:
            bool: Whether the hyperlink is found and matches the criteria.
        """
        for element in document.get("body", {}).get("content", []):
            if "paragraph" in element:
                for parElement in element["paragraph"].get("elements", []):
                    text_run = parElement.get("textRun")
                    print(text_run.get("content", ""))
                    if text_run and search_text in text_run.get("content", ""):
                        text_style = text_run.get("textStyle", {})
                        if "link" in text_style:
                            actual_url = text_style["link"].get("url", "")
                            if actual_url == expected_url:
                                return True
        return False

    @evaluation_handler("text_format_match")
    def text_format_match(
        self,
        title: str,
        text: str,
        font: str | None = None,
        size: int | None = None,
    ) -> None:
        """
        Evaluates if the text matches the specified formatting.
        """
        doc_ids = self.search_doc_by_title(title)
        if not doc_ids:
            raise FeedbackException(f"No document found with the title '{title}'.")

        for doc_id in doc_ids:
            document = self.get_document(doc_id)
            text_format = self.find_text_format(document, text)
            if text_format is None:
                continue  # Text not found in this document

            # Evaluate each formatting attribute
            if font and text_format.get("font") != font:
                raise FeedbackException(
                    f"Font does not match. Expected {font}, "
                    f"found {text_format.get('font')}."
                )
            if size and text_format.get("size") != size:
                raise FeedbackException(
                    f"Size does not match. Expected {size}, "
                    f"found {text_format.get('size')}."
                )

            return

        raise FeedbackException("Text not found.")

    @evaluation_handler("hyperlink_match")
    def hyperlink_match(self, title: str, text: str, url: str, exists: bool) -> None:
        """
        Evaluates if a hyperlink with the specified text and URL exists in the document.

        Args:
            title (str): The title of the document to search for.
            text (str): The text of the hyperlink to match.
            url (str): The URL the hyperlink should point to.

        Raises:
            FeedbackException: If the hyperlink does not match the expected criteria.
        """
        doc_ids = self.search_doc_by_title(title)
        hyperlink_exists = False
        if len(doc_ids) != 0:
            for doc_id in doc_ids:
                document = self.get_document(doc_id)
                hyperlink_exists = self.find_hyperlink(document, text, url)
        if hyperlink_exists != exists:
            raise FeedbackException(
                f"The error occured when checking the existence of hyperlink with "
                f"text '{text}' and URL '{url}' in  {title}."
                f"It should be {exists}."
            )

    @evaluation_handler("check_doc_exists")
    def check_doc_exists(
        self,
        title: str,
        exists: bool,
        content: str | None = None,
    ) -> None:
        """
        Checks if the document matches the given parameters.

        Args:
            title (str): Document title.
            exists (bool): Whether the document should exist.
            content (str | None): Document content.

        Raises:
            FeedbackException: If the document exists does not match the expected value.

        Returns:
            None
        """
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
            raise FeedbackException(
                f"The error occured when checking the existence of {title}. "
                f"It should be {exists}."
            )

    @reset_handler("create_document")
    def create_document(
        self,
        title: str,
        content: str = "",
        hyperlink: dict[str, str] | None = None,
    ) -> dict:
        """
        Creates a document with the given title and content.

        Args:
            title (str): Document title.
            content (str): Document content.

        Returns:
            dict: Document information.
        """
        body = {"title": title}
        doc = self.service.documents().create(body=body).execute()
        document_id = doc["documentId"]

        requests = []
        # Append the main content text first, if provided
        requests.append(
            {
                "insertText": {
                    "location": {
                        "index": 1,
                    },
                    "text": content + "\n",
                }
            }
        )

        if hyperlink is not None:
            # Calculate the index to insert the hyperlink based on content length
            hyperlink_start_index = len(content) + 1 if content else 1
            hyperlink_end_index = hyperlink_start_index + len(hyperlink["text"])

            # Insert hyperlink text
            requests.append(
                {
                    "insertText": {
                        "location": {
                            "index": hyperlink_start_index,
                        },
                        "text": hyperlink["text"],
                    }
                }
            )

            # Apply the hyperlink style to the inserted text
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": hyperlink_start_index,
                            "endIndex": hyperlink_end_index,
                        },
                        "textStyle": {"link": {"url": hyperlink["url"]}},
                        "fields": "link",
                    }
                }
            )

        self.service.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()

        return doc

    @reset_handler("delete_document")
    def delete_document(self, title: str, content: str | None = None) -> None:
        """
        Deletes a document with the given title and content.

        Args:
            title (str): Document title.
            content (str): Document content.

        Returns:
            None
        """
        doc_ids = self.search_doc_by_title(title)
        if len(doc_ids) != 0:
            for doc_id in doc_ids:
                if content is None:
                    self.delete_doc_by_id(doc_id)
                else:
                    if self.drive_service.compare_file_content(doc_id, content):
                        self.delete_doc_by_id(doc_id)
