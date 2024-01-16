import json

from playground.agent.teacher_forcing_agent import TeacherForcingAgent
from playground.desktop_env.computer.env import ComputerEnv
from playground.desktop_env.eval.evaluator_helper import evaluator_router


def test_vscode(
    computer_env: ComputerEnv,
) -> None:
    config_file = "playground/desktop_env/eval/tasks/vscode.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)
    agent = TeacherForcingAgent(env=computer_env)

    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config)
        comb.reset()

        instruction = task_config["intent_template"].format(
            **task_config["instantiation_dict"]
        )
        agent.reset(
            instruction=instruction,
        )
        agent.run()

        score = comb()
        assert score == 1.0
