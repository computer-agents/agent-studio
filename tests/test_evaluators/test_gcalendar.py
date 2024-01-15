import json

from agent.teacher_forcing_agent import TeacherForcingAgent
from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import evaluator_router


def test_calendar(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/tasks/gcalendar.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)
    with open("config/environments.json", "r") as f:
        env_configs = json.load(f)
    agent = TeacherForcingAgent(env=computer_env)

    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config, env_configs)
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
            reference_action_sequence = None
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
