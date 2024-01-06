from desktop_env.computer.env import ComputerEnv
from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarEvaluator


def test_calendar(
    computer_env: ComputerEnv,
) -> None:
    evaluator = GoogleCalendarEvaluator()

    action_seq = """from desktop_env.eval.google_evaluators.calendar_evaluator import GoogleCalendarService

gcalendar_service = GoogleCalendarService(token_path="token.json")
# Create an event
event = gcalendar_service.create_event(
        summary='Meeting with Team',
        location='Office',
        description='Discuss project status',
        start_time='2024-01-05T09:00:00',
        end_time='2024-01-05T10:00:00',
        attendees=['example@email.com']
    )
print(f"Created event: {event.get('htmlLink')}")

event_info = gcalendar_service.get_event(event_id=event.get('id'))
print(json.dumps(event_info, indent=2))

# Search events
events = gcalendar_service.search_events(start_time='2024-01-05T00:00:00Z', end_time='2024-01-05T23:59:59Z')
print(json.dumps(events, indent=2))

# Delete an event
assert gcalendar_service.delete_event(event_id=event.get('id')) == True
"""

    for chunk in computer_env.run("python", action_seq):
        print(chunk)
    assert evaluator("desktop_env/eval/examples/google_calendar.json") == 1.0

    print("Succ")
