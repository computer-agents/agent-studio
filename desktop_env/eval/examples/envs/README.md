# Environment JSON Composition Guide

This guide provides instructions for creating a valid environment JSON file, which configures the environment for task evaluations. The file includes details about the applications used, their settings, environment intents, and predefined environments.

## Structure Overview

Your environment JSON file should contain the following properties:

- `applications`: A list of applications used in the environment.
- `applications_settings`: Settings specific to each application.
- `intent`: A description or intent of this environment setup.
- `environments`: Detailed configurations for each application environment.

## Detailed Structure

### Applications

- `type`: array of strings
- Description: Names of the applications used in this environment.

### Applications Settings

- `type`: object
- Description: Contains settings for each application listed in `applications`.
- Structure: Each key should be the name of an application, and its value should be an object containing specific settings for that application.

#### Example for Google Calendar Settings:

```json
"google_calendar": {
    "token_path": "PATH_TO_YOUR/token.json"
}
```

### Intent

- `type`: string
- Description: A detailed description of this environment for agent.

### Environments

- `type`: object
- Description: Detailed configurations for each environment.
- Structure: Each key is an environment name, and its value is an array of objects representing different states or data of the environment.

#### Example for Google Calendar Environment:

```json
"google_calendar": [
    {
        "event": {
            "summary": "Meeting with Team",
            "location": "Office",
            // ... additional event details ...
        }
    },
    {
        "event": {
            "summary": "See doctor",
            "location": "Clinic",
            // ... additional event details ...
        }
    }
]
```

## Example Environment JSON

```json
{
    "applications": ["google_calendar"],
    "applications_settings": {
        "google_calendar": {
            "token_path": "token.json"
        }
    },
    "intent": "Add some introductions to this environment",
    "environments": {
        "google_calendar": [
            {
                "event": {
                    "summary": "Meeting with Team",
                    "location": "Office",
                    "description": "Discuss project status",
                    "start": {"dateTime": "2024-01-05T10:00:00+01:00"},
                    "end": {"dateTime": "2024-01-05T11:00:00+01:00"}
                }
            },
            {
                "event": {
                    "summary": "See doctor",
                    "location": "Clinic",
                    "description": "Discuss current health status",
                    "start": {"dateTime": "2024-01-05T15:00:00+01:00"},
                    "end": {"dateTime": "2024-01-05T16:00:00+01:00"}
                }
            }
        ]
    }
}
```

### Scope
Each JSON part will be parse by different part of the evaluator. Here's the rule.

```json
{
    "applications": "Not used yet",
    "applications_settings": {
        "EVALUATOR_NAME": "For evaluator, e.g. google_evaluators/calendar_evaluator.py"
    },
    "intent": "For Agents",
    "environments": {
        "ENV_NAME1": "Not used yet",
        "ENV_NAME2": "Not used yet"
    }
}
```

## Validation

Ensure that your JSON file strictly adheres to the defined schema. You can run `scripts/json_check.sh` to check if JSON files are valid.
