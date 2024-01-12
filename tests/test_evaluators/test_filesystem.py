import json

from agent.teacher_forcing_agent import TeacherForcingAgent
from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import evaluator_router


def test_filesystem(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/tasks/filesystem.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)
    with open("config/environments.json", "r") as f:
        env_configs = json.load(f)
    agent = TeacherForcingAgent(env=computer_env)

    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config, env_configs)
        comb.reset()
        oracle_trajectory = comb.get_oracle_trajectory()
        instruction = task_config["intent_template"].format(
            **task_config["instantiation_dict"]
        )
        agent.reset(
            instruction=instruction,
            oracle_trajectory=oracle_trajectory,
        )
        agent.run()
        score = comb()
        assert score == 1.0
