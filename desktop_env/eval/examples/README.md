# Task JSON Composition Guide

This guide provides instructions for creating a valid JSON file based on the specified schema for task evaluation. The JSON file is structured to include details about the environment, tasks, and various parameters related to the evaluation process.

## Structure Overview

Your JSON file should have the following top-level properties:

- `environment`: A string specifying the environment.
- `score_weight`: A number indicating the weight of this evaluation.
- `tasks`: An array of task objects, each representing a specific task.

## Detailed Structure

### Environment

- `type`: string
- Description: Task environment. This should match the file name in `desktop_env/eval/examples/envs`. Anything related to the environment should be there.

### Score Weight

- `type`: number
- Description: The weight of the score in this evaluation. The final score can be a weighted average of all evaluations (Not implemented!).

### Tasks

An array of objects, where each object represents a task and must include:

- `task_id`: (integer) Unique identifier for the task.
- `available_apis`: (array of strings) List of available APIs for the task (Maybe this can be a list of object, Not decided!).
- `score`: (number) Score associated with the task.
- `reset`: (boolean) Indicates whether to reset the environment state before the task.
- `intent_template`: (string, null) Template for the intent, can be null for now, but will only allow string later.
- `instantiation_dict`: (object, null) Dictionary for instantiation, can be null for now, but will only allow object later.
- `evals`: (array) Array of evaluation objects.
- `reference_action_sequence`: (object, null) Sequence of reference actions (Not implemented yet!).

#### Evals

Each object in the `evals` array must include:

- `eval_type`: (string) Type of evaluation. This must match one of the `Evaluator.evaluator_name()`. 
- `reference_answers`: (object) Object containing reference answers for evaluation.
- `extra_info`: (object) Additional information for the evaluation.

### Example

```json
{
    "environment": "your_env_name",
    "score_weight": 1.0,
    "tasks": [
        {
            "task_id": 0,
            "available_apis": [
                // ... list of available APIs for Agent ...
            ],
            "score": 1.0,
            "reset": false,
            "intent_template": "Write down your task description",
            "instantiation_dict": null,
            "evals": [
                {
                    "eval_type": "google_calendar",
                    "reference_answers": {
                        // ... reference answers ...
                    },
                    "extra_info": {
                        // ... extra information ...
                    }
                }
            ],
            "reference_action_sequence": {
                "action_sequence": []
            }
        }
    ]
}
```

### Scope
Each JSON part will be parse by different part of the evaluator. Here's the rule.

```json
{
    "environment": "For evaluator_helper.py",
    "score_weight": "For evaluator_helper.py",
    "tasks": [
        {
            "task_id": "For evaluator_helper.py",
            "available_apis": "For Agents",
            "score": "For evaluator_helper.py",
            "reset": "Not used yet",
            "intent_template": "For Agents",
            "instantiation_dict": "For Agents",
            "evals": [
                {
                    "eval_type": "For evaluator_helper.py",
                    "reference_answers": "For evaluator, e.g. google_evaluators/calendar_evaluator.py",
                    "extra_info": "For evaluator, e.g. google_evaluators/calendar_evaluator.py"
                }
            ],
            "reference_action_sequence": {
                "action_sequence": "Not used yet"
            }
        }
    ]
}
```

## Validation

Ensure that your JSON file strictly adheres to the defined schema. You can run `scripts/json_check.sh` to check if JSON files are valid.
