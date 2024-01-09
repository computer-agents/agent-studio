from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.envs.environment_helper import environment_init
from desktop_env.eval.evaluator_helper import eval_json


def test_calendar(
    computer_env: ComputerEnv,
) -> None:
    comb = environment_init("desktop_env/eval/examples/gcalendar_env_task.json")

    score = eval_json("desktop_env/eval/examples/gcalendar_env_task.json")
    assert score == 0.0

    comb.reset()

    score = eval_json("desktop_env/eval/examples/gcalendar_env_task.json")
    assert score == 1.0

    del comb

    score = eval_json("desktop_env/eval/examples/gcalendar_env_task.json")
    assert score == 0.0
