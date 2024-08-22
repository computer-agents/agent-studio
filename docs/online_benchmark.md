# Custom real-world benchmarks

## Example tasks

The example task configurations are located in `evals/datasets/online_benchmarks`.

- **Level 1**: `filesystem.json`
- **Level 2**: `gcalendar.json`, `gdocs.json`, and `gmail.json`.
- **Level 3**: ``

We also provide more auto-evaluators on other applications in `agent_studio/envs/desktop_env/evaluators`, such as Google Drive, Google Slides, etc.

## Evaluate agents on custom tasks

### Before You Start

You should note that the toolkit may do some **non-reversible actions**, such as deleting files, creating files, running commands, and deleting Google Calendar events. Please make sure you are hosting the toolkit in **a safe environment (E.g. virtual machine or docker) or have backups of your data.** Some tasks may require you to provide API keys. Before running the tasks, **please make sure the account doesn't have important data.**

### Local

#### Non-GUI tasks

For Level-1 tasks without Google API usage (e.g., OS-related tasks), you can directly run:

For example:

```bash
as-online-benchmark --task_configs_path evals/datasets/online_benchmarks/level_1/filesystem.json --model gemini-1.0-pro-001
```

You can set `need_human_confirmation` to True in `agent_studio/config/config.py` to do safety check before each action execution. You can add `--help` for more args.

By default, you can check `logs` to see the full logs and result jsonl files.

For Level-2 tasks requiring Google API usage, kindly enable Google APIs, configure OAuth, download the credentials following instructions [here](https://developers.google.com/docs/api/quickstart/python#set_up_your_environment), specify the credential path in `agent_studio/config/api_key.json`. When you run the benchmark for the first time, you will be prompted to visit several URLs to authorize Google Docs, Drives, etc. The corresponding token json files like `docs_token.json` will be saved in `agent_studio/config`.

Start benchmarking:

```bash
as-online-benchmark --task_configs_path evals/datasets/online_benchmarks/level_2/gcalendar.json --model gemini-1.0-pro-001
as-online-benchmark --task_configs_path evals/datasets/online_benchmarks/level_2/gdocs.json --model gemini-1.0-pro-001
as-online-benchmark --task_configs_path evals/datasets/online_benchmarks/level_2/gmail.json --model gemini-1.0-pro-001
```

#### GUI tasks

This setup is suitable for evaluating agents in visual tasks. For reproducibility, we use a Ubuntu docker container connected via VNC remote desktop.

```bash
as-online-benchmark --task_configs_path evals/datasets/online_benchmarks/level_3/desktop_hard.json --model gemini-1.5-flash-001 --remote --end_idx 1 --render
as-online-benchmark --task_configs_path evals/datasets/online_benchmarks/level_3/vscode.json --model gemini-1.5-flash-001 --remote ...
```

## Add more tasks

To add custom tasks for benchmarking agents in the wild, you can add a task.jsonl files according to ...

This guide provides instructions for creating a valid Task JSON file in accordance with the specified schema for task evaluation. The JSON file combines details about the environment and tasks, along with various parameters pertinent to the evaluation process.

### Task Structure

- `task_id`: A unique identifier for the task.
- `instruction`: The task instuction.
- `tags`: (optional) A list of tags to categorize the task.
- `visual`: 
- `max_steps`: 
- `evals`: A list of evaluators to evaluate the task. Each object in the list should include:
    - `eval_type`: The type of evaluation to be conducted. This should match the name of the evaluator.
    - `eval_procedure`: (optional) Contains the evaluation procedure and the reference answers.
    - `reset_procedure`: (optional) A list of actions to reset environment before the task.

Example task:

```json
{
    "task_id": "uuid string",
    "instruction": "Task instruction for the agent to complete",
    "tags": ["tag1", "tag2"],
    "visual": false,
    "max_steps": 1,
    "evals": [
        {
            "eval_type": "evaluator1",
            "eval_procedure": [
                {
                    "eval_func_name": {
                        "param1": "value1",
                        "param2": "value2",
                    }
                }
            ],
            "reset_procedure": [
                {
                    "reset_func_name": {
                        "param1": "value1",
                        "param2": "value2",
                    }
                }
            ]
        }
    ]
}
```
