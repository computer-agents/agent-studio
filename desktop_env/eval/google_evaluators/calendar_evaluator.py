from pathlib import Path

from desktop_env.eval.google_evaluators.google_base_evaluator import GEvaluator


class GoogleCalendarEvaluator(GEvaluator):
    def __init__(self, token_path: str) -> None:
        scopes = ["https://www.googleapis.com/auth/calendar"]
        super().__init__(
            scopes=scopes, 
            token_path=token_path, 
            service_name="calendar", 
            service_version="v3"
        )

    def list_calendars(self) -> list[dict] | None:
        try:
            page_token = None
            calendar_entry_list = []
            while True:
                calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
                for calendar_entry in calendar_list['items']:
                    calendar_entry_list.append(calendar_entry)

                page_token = calendar_list.get('nextPageToken')
                if not page_token:
                    break
            return calendar_entry_list
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def create_event(
            self, 
            summary: str | None, 
            location: str | None, 
            description: str | None, 
            start_time: str, 
            end_time: str, 
            attendees: list[str] | None =None,
            calendar_id: str | None ='primary'
            ) -> dict | None:
        event = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'attendees': [{'email': attendee} for attendee in attendees] if attendees else [],
        }
        try:
            event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            return event
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def delete_event(self, event_id: str) -> bool:
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def get_event(self, event_id: str) -> dict | None:
        try:
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            return event
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def search_events(self, start_time: str, end_time: str) -> list[dict] | None:
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime').execute()
            return events_result.get('items', [])
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def __call__(
        self,
        config_file: Path | str,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        score = 1.0
        gcalendar_evaluator = GoogleCalendarEvaluator(token_path="token.json")
        # TODO
        return score
    

if __name__ == "__main__":
    import json
    gcalendar_evaluator = GoogleCalendarEvaluator(token_path="token.json")
    
    # Create an event
    event = gcalendar_evaluator.create_event(
            summary='Meeting with Team',
            location='Office',
            description='Discuss project status',
            start_time='2024-01-05T09:00:00',
            end_time='2024-01-05T10:00:00',
            attendees=['example@email.com']
        )
    print(f"Created event: {event.get('htmlLink')}")

    event_info = gcalendar_evaluator.get_event(event_id=event.get('id'))
    print(json.dumps(event_info, indent=2))

    # Search events
    events = gcalendar_evaluator.search_events(start_time='2024-01-01T00:00:00Z', end_time='2024-01-31T23:59:59Z')
    print(json.dumps(events, indent=2))

    # Delete an event
    assert gcalendar_evaluator.delete_event(event_id=event.get('id')) == True
