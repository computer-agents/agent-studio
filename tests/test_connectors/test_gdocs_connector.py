from typing import Any

from desktop_env.eval.connectors.gspace.gdocs import GoogleDocsService


def test_gdocs_connector() -> None:
    token_path = "config/token.json"
    google_docs_service = GoogleDocsService(token_path)

    # 1. Create a new document
    new_document = google_docs_service.create_document("Test Document")
    document_id: Any = new_document.get("documentId")
    print(f"Created document with ID: {document_id}")

    # 2. Append text to the document
    google_docs_service.append_text(document_id, "Hello, this is a test document.\n")

    # 3. Replace some text
    google_docs_service.replace_text(document_id, "test", "sample")

    # 4. Get and print the title of the document
    title = google_docs_service.get_document_title(document_id)
    print(f"Document title: {title}")

    # 5. Delete a portion of text
    google_docs_service.delete_text(document_id, 10, 15)

    # 6. Insert a table
    google_docs_service.insert_table(document_id, 2, 3)  # 2 rows, 3 columns

    # 7. Delete the document
    google_docs_service.delete_document(document_id)
    print(f"Deleted document with ID: {document_id}")
