import json
import os

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.bridges.bridge_helper import bridge_init
from desktop_env.eval.evaluator_helper import eval_tasks


def test_joint(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/examples/joint_evaluation.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)

    env_comb = bridge_init("config/environments.json")

    score = eval_tasks(
        task_configs,
        env_comb,
    )
    assert score == 1.0

    # Test reset
    os.remove("tmp/test.txt")
    os.rmdir("tmp")
    score = eval_tasks(
        task_configs,
        env_comb,
    )
    assert score == 1.0
