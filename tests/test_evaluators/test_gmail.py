import json

from playground.desktop_env import ComputerEnv
from playground.desktop_env.eval.evaluator_helper import evaluator_router


def test_gmail(
    computer_env: ComputerEnv,
) -> None:
    config_file = "playground/desktop_env/eval/tasks/gmail.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)

    for task_config in task_configs:
        comb = evaluator_router(task_config)
        comb.reset()
        # Tip: run pytest with -s, and finish the task by hand during this input
        response = input(
            "Finish the task or answer the question, and press Enter to eval\n"
            f"The task is: {task_config['intent']}"
        )

        if len(response) > 0:
            score = comb(**{"response": response})
        else:
            score = comb()
        assert score == 1.0
