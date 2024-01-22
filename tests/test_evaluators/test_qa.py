import json

from playground.desktop_env import ComputerEnv
from playground.desktop_env.eval.evaluator_helper import evaluator_router


def test_qa(
    computer_env: ComputerEnv,
) -> None:
    config_file = "playground/desktop_env/eval/tasks/qa_level3.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)

    for task_config in task_configs:
        comb = evaluator_router(task_config)
        score = comb(
            **{"output": task_config["evals"][0]["eval_procedure"]["string_match"]}
        )
        assert score == 1.0
