import json

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import evaluator_router

agent_sim = {
    0: """
import json
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="config/token.json")
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]
# Create an event
event = gcalendar_service.create_event(
        summary='Meeting with Team',
        location='Office',
        description='Discuss project status',
        start_time='2024-01-05T10:00:00Z',
        end_time='2024-01-05T11:00:00Z',
        calendar_id=calendar_id,
    )
""",
    1: """
import json
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="config/token.json")
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]
# Create an event
event = gcalendar_service.create_event(
        summary='Meeting with Team',
        location='Office',
        description='Discuss project status',
        start_time='2024-01-05T10:00:00Z',
        end_time='2024-01-05T11:00:00Z',
        calendar_id=calendar_id,
    )
""",
    2: """
import os

with open("tmp/test.txt", "w") as f:
    f.write("Hello World!")
""",
    3: """
import json
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="config/token.json")
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

events_result = (
    gcalendar_service.service.events()
    .list(calendarId=calendar_id, singleEvents=True)
    .execute()
)
events = events_result.get("items", [])

with open("tmp/calendar.txt", "w") as f:
    for event in events:
        f.write(event["summary"] + "\\n")
""",
}


def test_calendar(
    computer_env: ComputerEnv,
) -> None:
    config_file = "desktop_env/eval/tasks/gcalendar_filesystem.json"
    with open(config_file, "r") as f:
        task_configs = json.load(f)
    with open("config/environments.json", "r") as f:
        env_configs = json.load(f)

    total_score = 0.0
    gained_score = 0.0
    for task_config in task_configs["tasks"]:
        comb = evaluator_router(task_config, env_configs)
        comb.reset()
        # Execute the Agent start #
        print(f"Executing {task_config['task_id']}")
        for chunk in computer_env.run("python", agent_sim[task_config["task_id"]]):
            print(chunk)
        print(f"Done Executing {task_config['task_id']}")
        #  Execute the Agent end  #
        task_score = comb()
        gained_score += task_score * task_config["score"]
        total_score += task_config["score"]

    assert gained_score / total_score == 1.0, print(total_score, gained_score)
