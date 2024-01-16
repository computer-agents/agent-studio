from typing import Any

from playground.desktop_env.eval.connectors.gspace.gforms import GoogleFormsService


def test_gforms_connector() -> None:
    form_service = GoogleFormsService()

    # Create a new form
    form_body = {
        "info": {
            "title": "Quickstart form",
        }
    }
    new_form = form_service.create_form(form_body)
    form_id: Any = new_form["formId"]
    print(f"Created form with ID: {form_id}")

    # Add a question to the form
    question = {
        "title": ("In what year did the United States land a mission on" " the moon?"),
        "questionItem": {
            "question": {
                "required": True,
                "choiceQuestion": {
                    "type": "RADIO",
                    "options": [
                        {"value": "1965"},
                        {"value": "1967"},
                        {"value": "1969"},
                        {"value": "1971"},
                    ],
                    "shuffle": True,
                },
            }
        },
    }
    form_service.add_question(form_id, question, index=0)
    print("Added a question to the form")

    # Retrieve and print form details
    form_details = form_service.get_form(form_id)
    print("Form details:", form_details)
