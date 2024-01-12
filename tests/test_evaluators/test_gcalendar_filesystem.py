import json

from agent.teacher_forcing_agent import TeacherForcingAgent
from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import evaluator_router

agent_sim = {
    3: """
import json
from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
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
    4: """
import os
import json
from pathlib import Path

from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

event = gcalendar_service.create_event(
    summary="Follow-up Meeting",
    location="Conference Room",
    description="Discuss action points from last meeting",
    start_time="2024-03-08T10:00:00Z",
    end_time="2024-03-08T11:00:00Z",
    calendar_id=calendar_id,
)

path = "tmp/Documents/Meetings"
Path(path).mkdir(parents=True, exist_ok=True)
with open("tmp/Documents/Meetings/Meeting_Minutes_20240301.txt", "w") as f:
    f.write("Minutes of the meeting held on 2024-03-01")
    """,
    5: """
import os
import json
from pathlib import Path

from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

event = gcalendar_service.create_event(
    summary="Budget Review Follow-up",
    description="Reminder to prepare for the follow-up meeting",
    location="Conference Room",
    start_time="2024-04-22T09:00:00Z",
    end_time="2024-04-22T09:30:00Z",
    calendar_id=calendar_id,
)

path = "tmp/Meeting_Summaries"
Path(path).mkdir(parents=True, exist_ok=True)
with open("tmp/Meeting_Summaries/Budget_Review_Summary_20240415.txt", "w") as f:
    f.write("Summary of Budget Review meeting on 2024-04-15")
""",
    6: """
import os
import json
from pathlib import Path

from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

events = gcalendar_service.search_events_by_info(
    {
        "summary": "Team Sync",
        "start": {"dateTime": "2024-05-10T00:00:00Z"},
        "end": {"dateTime": "2024-05-10T01:00:00Z"}
    },
    calendar_id=calendar_id
)
assert len(events) == 1

gcalendar_service.update_event(
    events[0]["id"],
    {
        "summary": "Team Sync",
        "start": {"dateTime": "2024-05-12T14:00:00Z"},
        "end": {"dateTime": "2024-05-12T15:00:00Z"}
    },
    calendar_id=calendar_id
)
""",
    7: """
import os
import json
from pathlib import Path

from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

events = gcalendar_service.search_events_by_info(
    {
        "summary": "Team Sync",
        "start": {"dateTime": "2024-05-10T00:00:00Z"},
        "end": {"dateTime": "2024-05-10T01:00:00Z"}
    },
    calendar_id=calendar_id
)
assert len(events) == 1

gcalendar_service.update_event(
    events[0]["id"],
    {
        "summary": "Team Sync",
        "start": {"dateTime": "2024-05-12T14:00:00Z"},
        "end": {"dateTime": "2024-05-12T15:00:00Z"}
    },
    calendar_id=calendar_id
)
path = "tmp/Notifications"
Path(path).mkdir(parents=True, exist_ok=True)
with open("tmp/Notifications/Team_Sync_Rescheduled_20240512.txt", "w") as f:
    f.write("Team Sync meeting has been rescheduled to 2024-05-12 at 2:00 PM")
""",
    8: """
import os
import json
from pathlib import Path

from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

events = gcalendar_service.search_events_by_time_range(
    "2024-08-10T00:00:00Z",
    "2024-08-10T23:59:59Z",
    calendar_id=calendar_id
)
reference_event = {
    "summary": "Project Planning Meeting",
}
results = []
for event in events:
    if gcalendar_service.event_match_left(reference_event, event):
        results.append(event)

if len(events) > 0:
    path = "tmp/Meeting_Documents/Project_Planning_20240810"
    Path(path).mkdir(parents=True, exist_ok=True)
    with open(
        "tmp/Meeting_Documents/Project_Planning_20240810/Attendees.txt",
        "w") as f:
        f.write("List of Attendees")
    with open(
        "tmp/Meeting_Documents/Project_Planning_20240810/Agenda.txt",
        "w") as f:
        f.write("Meeting Agenda")
""",
    9: """
import os
import json
from pathlib import Path

from desktop_env.eval.connectors.gspace.gcalendar import GoogleCalendarService

gcalendar_service = GoogleCalendarService(
    credential_path="config/secrets/credentials.json"
)
with open("config/environments.json", "r") as f:
    env_configs = json.load(f)
    calendar_id = env_configs["google_calendar"]["env_settings"]["calendar_id"]

events = gcalendar_service.search_events_by_time_range(
    "2024-08-10T00:00:00Z",
    "2024-08-10T23:59:59Z",
    calendar_id=calendar_id
)
reference_event = {
    "summary": "Project Planning Meeting",
}
results = []
for event in events:
    if gcalendar_service.event_match_left(reference_event, event):
        results.append(event)

if len(results) > 0:
    path = "tmp/Meeting_Documents/Project_Planning_20240810"
    Path(path).mkdir(parents=True, exist_ok=True)
    with open(
        "tmp/Meeting_Documents/Project_Planning_20240810/Attendees.txt",
        "w") as f:
        f.write("List of Attendees")
    with open(
        "tmp/Meeting_Documents/Project_Planning_20240810/Agenda.txt",
        "w") as f:
        f.write("Meeting Agenda")
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
    agent = TeacherForcingAgent(env=computer_env)

    for task_config in task_configs["tasks"]:
        # if task_config["task_id"] != 8:
        #     continue
        comb = evaluator_router(task_config, env_configs)
        comb.reset()

        # Execute the Agent start #
        print(f"Executing {task_config['task_id']}")
        for chunk in computer_env.run("python", agent_sim[task_config["task_id"]]):
            print(chunk)
        print(f"Done Executing {task_config['task_id']}")
        #  Execute the Agent end  #

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
