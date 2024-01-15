# Task JSON Composition Guide

This guide provides instructions for creating a valid Task JSON file in accordance with the specified schema for task evaluation. The JSON file combines details about the environment and tasks, along with various parameters pertinent to the evaluation process.

## Structure Overview

Your Task JSON file should contain the following top-level properties:

- `environments`: A list of strings specifying the environments to be used. Any item in this list should match the keys in `playground/config/environments.json`
- `action_sequence_path`: The path to the annotated trajectories.
- `tasks`: A list of objects, each representing a specific task and must include:
    - `task_id`: (int) A unique identifier for the task.
    - `intent_template`: (string, null) A template describing the task's intent.
    - `instantiation_dict`: (object, null) A dictionary for instantiation details.
    - `evals`: A list of evaluation objects pertaining to the task. Each object in the list should include:
        - `eval_type`: (string) The type of evaluation to be conducted. This should match the name of the evaluator.
        - `eval_procedure`: (object) Contains the evaluation procedure and the reference answers.
        - `reset_procedure` (if provided) should include an object where the key is the environment name (e.g., "google_calendar") and the value is a list of actions to reset the state of that environment.

### Example Task JSON

```json
{
    "environments": ["google_calendar"],
    "action_sequence_path": "data/gcalendar.json",
    "tasks": [
        {
            "task_id": 0,
            "intent_template": "Instructions for Agent",
            "instantiation_dict": {},
            "evals": [
                {
                    "eval_type": "google_calendar",
                    "eval_procedure": {
                        "event_match": {
                            "summary": "Meeting with Team",
                            "location": "Office",
                            "description": "Discuss project status",
                            "start": {"dateTime": "2024-01-05T11:00:00+01:00"},
                            "end": {"dateTime": "2024-01-05T12:00:00+01:00"}
                        }
                    },
                    "reset_procedure": {
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
    ]
}
```

## Validation

Ensure that your Task JSON file adheres strictly to the defined schema. Utilize `scripts/json_check.sh` to verify the validity of your JSON files.
