import json
import os

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.envs.environment_helper import environment_init
from desktop_env.eval.evaluator_helper import eval_tasks


def test_calendar_env(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/examples/google_calendar_env.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)

    with open(
        os.path.join(
            "desktop_env/eval/examples/envs", f"{task_configs['environment']}.json"
        ),
        "r",
    ) as f:
        env_configs = json.load(f)

    env_comb = environment_init(
        os.path.join(
            "desktop_env/eval/examples/envs", f"{task_configs['environment']}.json"
        )
    )
    env_comb.reset()

    score = eval_tasks(
        task_configs,
        env_configs,
        env_comb,
    )
    assert score == 1.0
