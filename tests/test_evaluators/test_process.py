import json

from playground.agent.teacher_forcing_agent import TeacherForcingAgent
from playground.desktop_env import ComputerEnv
from playground.desktop_env.eval.evaluator_helper import evaluator_router


def test_vscode(
    computer_env: ComputerEnv,
) -> None:
    config_file = "playground/desktop_env/eval/tasks/process.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)
    agent = TeacherForcingAgent(env=computer_env)

    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config)
        comb.reset()

        action_sequence_path: str | None = task_configs.get(
            "action_sequence_path", None
        )
        if action_sequence_path is not None:
            with open(action_sequence_path, "r") as f:
                tasks = json.load(f)["tasks"]
                for t in tasks:
                    if t["task_id"] == task_config["task_id"]:
                        reference_action_sequence = t["reference_action_sequence"]
                        break
        else:
            reference_action_sequence = ""
        instruction = task_config["intent_template"].format(
            **task_config["instantiation_dict"]
        )
        agent.reset(
            instruction=instruction,
            reference_action_sequence=reference_action_sequence,
        )
        agent.run()

        score = comb()
        assert score == 1.0
