from typing import Any

from desktop_env.eval.connectors.gspace.gdocs import GoogleDocsService
from desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService


def test_gdocs_connector() -> None:
    credential_path = "config/credentials.json"
    google_docs_service = GoogleDocsService(credential_path)
    drive_service = GoogleDriveService(credential_path)

    # Create a new document
    new_document = google_docs_service.create_document("Test Document")
    document_id: Any = new_document.get("documentId")
    print(f"Created document with ID: {document_id}")

    # Get recently created document
    document = drive_service.get_recent_documents()
    print(document)

    # Append text to the document
    google_docs_service.append_text(document_id, "Hello, this is a test document.\n")

    # Replace some text
    google_docs_service.replace_text(document_id, "test", "sample")

    # Get and print the title of the document
    title = google_docs_service.get_document_title(document_id)
    print(f"Document title: {title}")

    # Delete a portion of text
    google_docs_service.delete_text(document_id, 10, 15)

    # Insert a table
    google_docs_service.insert_table(document_id, 2, 3)  # 2 rows, 3 columns

    drive_service.delete_file(file_id=document_id)
    print(f"Deleted document with ID: {document_id}")
