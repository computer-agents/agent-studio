# Task JSON Composition Guide

This guide provides instructions for creating a valid Task JSON file in accordance with the specified schema for task evaluation. The JSON file combines details about the environment and tasks, along with various parameters pertinent to the evaluation process.

## Structure Overview

Your Task JSON file should contain the following top-level properties:

- `environments`: An array specifying the environments to be used.
- `tasks`: An array of objects, each representing a specific task within the evaluation.

## Detailed Structure

### Environments

- `type`: array of strings
- Description: Lists the environments that will be used in the task evaluations. Any item in this list should match the keys in `config/environments.json`

### Tasks

An array of objects, where each object encapsulates a specific task and must include:

- `task_id`: (integer) A unique identifier for the task.
- `available_apis`: (array of strings) Specifies the APIs available for the task.
- `intent_template`: (string, null) A template describing the task's intent.
- `instantiation_dict`: (object, null) A dictionary for instantiation details.
- `evals`: (array) An array of evaluation objects pertaining to the task.
- `reference_action_sequence`: (object, null) A sequence of reference actions for the task (optional).
- `reset_actions`: (object, null) Actions to reset the environment states (optional).

#### Evals

Each object in the `evals` array should include:

- `eval_type`: (string) The type of evaluation to be conducted. This should match the name of the evaluator.
- `reference_answers`: (object) Contains reference answers for the evaluation.

#### Reset Actions

`reset_actions` (if provided) should include:

- An object where the key is the environment name (e.g., "google_calendar") and the value is an array of actions to reset the state of that environment.

### Example Task JSON

```json
{
    "environments": ["google_calendar"],
    "tasks": [
        {
            "task_id": 0,
            "available_apis": ["GoogleCalendarService"],
            "intent_template": null,
            "instantiation_dict": null,
            "evals": [
                {
                    "eval_type": "google_calendar",
                    "reference_answers": {
                        "event_match": {
                            "summary": "Meeting with Team",
                            "location": "Office",
                            "description": "Discuss project status",
                            "start": {"dateTime": "2024-01-05T11:00:00+01:00"},
                            "end": {"dateTime": "2024-01-05T12:00:00+01:00"}
                        }
                    }
                }
            ],
            "reference_action_sequence": {
                "action_sequence": []
            },
            "reset_actions": {
                "google_calendar": [
                    {
                        "clear_calendar": {}
                    },
                    {
                        "create_event": {
                            "summary": "Meeting with Team",
                            "location": "Office",
                            "description": "Discuss project status",
                            "start": {"dateTime": "2024-01-05T10:00:00Z"},
                            "end": {"dateTime": "2024-01-05T11:00:00Z"}
                        }
                    }
                ]
            }
        }
    ]
}
```

## Validation

Ensure that your Task JSON file adheres strictly to the defined schema. Utilize `scripts/json_check.sh` to verify the validity of your JSON files.
