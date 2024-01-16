from typing import Any

from playground.desktop_env.eval.connectors.gspace.gdrive import GoogleDriveService
from playground.desktop_env.eval.connectors.gspace.gslides import GoogleSlidesService


def test_gdocs_connector() -> None:
    slides_service = GoogleSlidesService()

    # Create a new presentation
    presentation_title = "Test Presentation"
    presentation = slides_service.create_presentation(title=presentation_title)
    presentation_id: Any = presentation.get("presentationId")
    print(f"Created presentation with ID: {presentation_id}")

    # Add a slide
    slides_service.add_slide(presentation_id=presentation_id)
    print("Added a slide.")

    # Retrieve the slide IDs
    slide_ids = slides_service.get_slide_ids(presentation_id=presentation_id)
    if not slide_ids:
        print("No slides found.")
        return
    print("Slide IDs:", slide_ids)
    slide_object_id = slide_ids[0]  # Using the first slide's ID
    print(f"Using slide ID: {slide_object_id}")

    # Create a text box
    textbox_id = slides_service.create_textbox(
        presentation_id, slide_object_id, x=100, y=100, width=300, height=100
    )
    if textbox_id:
        # Add text to the newly created text box
        text_to_add = "Hello, Google Slides!"
        slides_service.add_text_to_slide(
            presentation_id=presentation_id,
            page_id=textbox_id,
            text=text_to_add,
        )
        print(f"Added text to the text box with ID: {textbox_id}")
    else:
        print("Failed to create a text box.")

    # Replace text in the slide
    slides_service.replace_text_in_slide(presentation_id, "Hello", "Welcome to")
    print("Replaced text in the slide.")

    # Delete a slide
    slides_service.delete_slide(presentation_id, slide_object_id)
    print("Deleted a slide.")

    # Delete the presentation
    drive_service = GoogleDriveService()
    drive_service.delete_file(file_id=presentation_id)
    print(f"Deleted presentation with ID: {presentation_id}")
