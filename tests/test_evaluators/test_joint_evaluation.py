import json
import shutil

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import eval_tasks


def test_joint(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/examples/joint_evaluation.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)
    with open("config/environments.json", "r") as f:
        env_configs = json.load(f)

    score = eval_tasks(
        task_configs,
        env_configs,
    )
    assert score == 1.0

    # Test reset
    shutil.rmtree("tmp")
    score = eval_tasks(
        task_configs,
        env_configs,
    )
    assert score == 1.0
