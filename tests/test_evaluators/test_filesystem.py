import json
import os

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.bridges.bridge_helper import environment_init
from desktop_env.eval.evaluator_helper import eval_tasks


def test_filesystem(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/examples/filesystem.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)

    env_comb = environment_init("config/environments.json")

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/test.txt", "w") as file:
        file.write("Hello World!")
    os.chmod("tmp/test.txt", 0o644)
    os.chmod("tmp", 0o775)
    score = eval_tasks(
        task_configs,
        env_comb,
    )
    assert score == 1.0, score

    os.remove("tmp/test.txt")
    score = eval_tasks(
        task_configs,
        env_comb,
    )
    assert score == (2.0 + 0.0) / (1.0 + 2.0) * 1.0, score

    os.rmdir("tmp")
    score = eval_tasks(
        task_configs,
        env_comb,
    )
    assert score == 0.0, score
