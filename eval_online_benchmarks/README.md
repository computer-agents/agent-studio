# Real-world online benchmarks

We provide 205 single-API, single-GUI, and compositional tasks for online benchmarking. We provide a Docker image for reproducible and reliable online benchmarks. Our tools also allow for convenient task customization.

## Setup Docker Image

First, please follow the instructions in the [README](../README.md) to install the AgentStudio python package and setup API keys.

We provide a lightweight Dockerfile of Ubuntu 22.04 for reproducible and reliable online benchmarks.

```bash
docker build -f dockerfiles/Dockerfile.ubuntu22.04.amd64 . -t agent-studio:latest
```

Run Docker:

```bash
docker run -d -e RESOLUTION=1024x768 -p 6080:80 -p 5900:5900 -p 8000:8000 -e VNC_PASSWORD=123456 -v /dev/shm:/dev/shm -v ${PWD}/agent_studio/config/:/home/ubuntu/agent_studio/agent_studio/config -v ${PWD}/eval_online_benchmarks/files:/home/ubuntu/agent_studio/data:ro agent-studio:latest
```

> You can also replace `-d` to `-it` to use interactive mode. If successful, you should see logs with a bunch of success followed by `INFO  Listening on http://localhost:6079` in the output.

You can browse `http://127.0.0.1:6080` to interact with the remote machine through a browser. The port `6080`, `5900`, and `8000` are exposed for noVNC, VNC server, and AgentStudio HTTP, respectively.

## Task Description

The tasks are located in `eval_online_benchmarks/tasks`, and the associated files are located in `eval_online_benchmarks/files`. The tasks are categorized into `single_api`, `single_gui`, and `compositional`.

## Start Evaluation

### Before You Start

You should note that agents may do some **non-reversible actions**, such as deleting files, creating files, running commands, and deleting Google Calendar events. Please make sure you have backups of your data. Some tasks may require you to provide API keys. Before running the tasks, **please make sure the account doesn't have important data.**

### Single-API Tasks

Start benchmarking:

```bash
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/filesystem --model gemini-1.0-pro-001
```

> You can set `need_human_confirmation=True` in `agent_studio/config/config.py` to do safety check before each action execution. You can add `--help` to explore more args.

By default, you can check `logs` to see the full logs and result jsonl files.

> Google service related tasks requiring Google API usage, kindly enable Google APIs, configure OAuth, download the credentials following instructions [here](https://developers.google.com/docs/api/quickstart/python#set_up_your_environment), specify the credential path in `agent_studio/config/api_key.json`. When you run the benchmark for the first time, you will be prompted to visit several URLs to authorize Google Docs, Drives, etc. The corresponding token json files like `docs_token.json` will be saved in `agent_studio/config`.

```bash
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/vscode/ --model gemini-1.0-pro-001
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/docs --model gemini-1.0-pro-001
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/filesystem --model gemini-1.0-pro-001
```

### Single-GUI Tasks

This setup is suitable for evaluating agents in visual tasks. For reproducibility, we use a Ubuntu docker container connected via VNC remote desktop.

```bash
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/vscode/ --model gemini-1.5-flash-001 --remote --render
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/vscode/ --model gemini-1.5-flash-001 --remote ...
```

We also provide more auto-evaluators on other applications in `agent_studio/envs/desktop_env/evaluators`, such as Telegram, Google Slides, etc.

### Compositional Tasks

```bash
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/compositional --model gemini-1.0-pro-001
```

## Add Tasks

### Human Evaluation

In case you want to debug or evaluate human performance, this testsuite also supports human evaluation. To enter human evaluation mode, you should set `--agent` to `human` and set `--need_human_confirmation` to True. During the evaluation, the script will popup "Confirm when you finish" after resetting the task. You can now do the task manually in any vnc viewer. After finishing the task, you can confirm the popup message to see the evaluation result. **You should only confirm the popup message after you have finished the task.**

Example command to start human evaluation on vscode tasks:

```bash
as-online-benchmark --task_configs_path eval_online_benchmarks/tasks/basic/vscode/ --model gemini-1.5-flash-001 --agent human --remote --render --need_human_confirmation
```

## Add more tasks

To add custom tasks for benchmarking agents in the wild, you can add a task.jsonl files according to ...

This guide provides instructions for creating a valid Task JSON file in accordance with the specified schema for task evaluation. The JSON file combines details about the environment and tasks, along with various parameters pertinent to the evaluation process.

### Task Structure

-   `task_id`: A unique identifier for the task.
-   `instruction`: The task instuction.
-   `tags`: (optional) A list of tags to categorize the task.
-   `visual`:
-   `max_steps`:
-   `evals`: A list of evaluators to evaluate the task. Each object in the list should include:
    -   `eval_type`: The type of evaluation to be conducted. This should match the name of the evaluator.
    -   `eval_procedure`: (optional) Contains the evaluation procedure and the reference answers.
    -   `reset_procedure`: (optional) A list of actions to reset environment before the task.

Example task:

```json
{
    "task_id": "uuid string",
    "instruction": "Task instruction for the agent to complete",
    "tags": ["tag1", "tag2"],
    "visual": false,
    "max_steps": 1,
    "eval_procedure": [
        {
            "evaluator": "evaluator1",
            "function": "function1",
            "params": {
                "param1": "value1"
            }
        }
    ],
    "reset_procedure": [
        {
            "evaluator": "evaluator2",
            "function": "function1",
            "params": {
                "param1": "value1",
                "param2": "value2"
            }
        }
    ]
}
```
