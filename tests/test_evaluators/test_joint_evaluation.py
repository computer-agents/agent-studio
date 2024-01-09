import json
import os

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.envs.environment_helper import environment_init
from desktop_env.eval.evaluator_helper import eval_tasks


def test_joint(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/examples/joint_evaluation.json"
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

    action_seq_create = """
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="token.json")
# Create an event
event = gcalendar_service.create_event(
        summary='Meeting with Team',
        location='Office',
        description='Discuss project status',
        start_time='2024-01-05T10:00:00Z',
        end_time='2024-01-05T11:00:00Z'
    )
"""

    for chunk in computer_env.run("python", action_seq_create):
        print(chunk)

    score = eval_tasks(
        task_configs,
        env_configs,
        env_comb,
    )
    assert score == 1.0

    action_seq_del = """
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="token.json")
# Search events
events = gcalendar_service.search_events(
    start_time='2024-01-05T10:00:00Z',
    end_time='2024-01-05T11:59:59Z'
    )

# Delete an event
assert gcalendar_service.delete_event(event_id=events[0].get('id')) == True
"""
    for chunk in computer_env.run("python", action_seq_del):
        print(chunk)

    score = eval_tasks(
        task_configs,
        env_configs,
        env_comb,
    )
    assert score == 0.0


if __name__ == "__main__":
    computer_env = ComputerEnv()
    test_joint(computer_env)
