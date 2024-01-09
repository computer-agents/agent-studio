import os

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import eval_json


def test_calendar(
    computer_env: ComputerEnv,
) -> None:
    os.makedirs("tmp", exist_ok=True)
    with open("tmp/test.txt", "w") as file:
        file.write("Hello World!")
    os.chmod("tmp/test.txt", 0o644)
    os.chmod("tmp", 0o775)
    score = eval_json("desktop_env/eval/examples/filesystem.json")
    assert score == 1.0, score

    os.remove("tmp/test.txt")
    score = eval_json("desktop_env/eval/examples/filesystem.json")
    assert score == (2.0 + 0.0) / (1.0 + 2.0) * 1.0, score

    os.rmdir("tmp")
    score = eval_json("desktop_env/eval/examples/filesystem.json")
    assert score == 0.0, score
