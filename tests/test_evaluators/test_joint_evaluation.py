import os

from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.evaluator_helper import eval_json


def test_calendar(
    computer_env: ComputerEnv,
) -> None:
    action_seq_create = """
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="token.json")
# Create an event
event = gcalendar_service.create_event(
        summary='Meeting with Team',
        location='Office',
        description='Discuss project status',
        start_time='2024-01-05T09:00:00',
        end_time='2024-01-05T10:00:00'
    )
"""

    for chunk in computer_env.run("python", action_seq_create):
        print(chunk)

    score = eval_json("desktop_env/eval/examples/joint_evaluation.json")
    assert score == 0.0

    os.makedirs("tmp", exist_ok=True)
    with open("tmp/test.txt", "w") as file:
        file.write("Hello World!")
    os.chmod("tmp/test.txt", 0o644)
    os.chmod("tmp", 0o775)
    score = eval_json("desktop_env/eval/examples/joint_evaluation.json")
    assert score == 1.0

    action_seq_del = """
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="token.json")
# Search events
events = gcalendar_service.search_events(
    start_time='2024-01-05T09:00:00Z',
    end_time='2024-01-05T10:59:59Z'
    )

# Delete an event
assert gcalendar_service.delete_event(event_id=events[0].get('id')) == True
"""
    for chunk in computer_env.run("python", action_seq_del):
        print(chunk)
    os.remove("tmp/test.txt")
    os.rmdir("tmp")
    score = eval_json("desktop_env/eval/examples/joint_evaluation.json")
    assert score == 0.0
