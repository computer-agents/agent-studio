from desktop_env.eval.envs.environment import Environment
from desktop_env.eval.envs.gspace.gservice import GoogleService


class GoogleCalendarService(GoogleService):
    def __init__(self, token_path: str) -> None:
        scopes = ["https://www.googleapis.com/auth/calendar"]
        super().__init__(
            scopes=scopes,
            token_path=token_path,
            service_name="calendar",
            service_version="v3",
        )

    def list_calendars(self) -> list[dict]:
        page_token = None
        calendar_entry_list = []
        while True:
            calendar_list = (
                self.service.calendarList().list(pageToken=page_token).execute()
            )
            for calendar_entry in calendar_list["items"]:
                calendar_entry_list.append(calendar_entry)

            page_token = calendar_list.get("nextPageToken")
            if not page_token:
                break
        return calendar_entry_list

    def create_calendar(self, calendar_info: dict) -> dict[str, str]:
        created_calendar = self.service.calendars().insert(body=calendar_info).execute()
        return created_calendar

    def delete_calendar(self, calendar_id: str) -> bool:
        try:
            self.service.calendars().delete(calendarId=calendar_id).execute()
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def find_calendar_by_id(self, id: str) -> dict[str, str]:
        calendar_entry_list = self.list_calendars()
        for calendar_entry in calendar_entry_list:
            if calendar_entry["id"] == id:
                return calendar_entry
        return {}

    def clear_calendar(self, calendar_id: str) -> None:
        events_result = (
            self.service.events()
            .list(calendarId=calendar_id, singleEvents=True)
            .execute()
        )
        events = events_result.get("items", [])

        for event in events:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event["id"]
            ).execute()

    def create_event(
        self,
        summary: str | None,
        location: str | None,
        description: str | None,
        start_time: str,
        end_time: str,
        attendees: list[str] | None = None,
        calendar_id: str | None = "primary",
        time_zone: str | None = "UTC",
    ) -> dict[str, str]:
        event_info = {
            "summary": summary,
            "location": location,
            "description": description,
            "start": {
                "dateTime": start_time,
                "timeZone": time_zone,
            },
            "end": {
                "dateTime": end_time,
                "timeZone": time_zone,
            },
            "attendees": [{"email": attendee} for attendee in attendees]
            if attendees
            else [],
        }
        event = (
            self.service.events()
            .insert(calendarId=calendar_id, body=event_info)
            .execute()
        )
        return event

    def delete_event(self, event_id: str, calendar_id: str = "primary") -> bool:
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            return False

    def get_event(self, event_id: str, calendar_id: str = "primary") -> dict[str, str]:
        event = (
            self.service.events()
            .get(calendarId=calendar_id, eventId=event_id)
            .execute()
        )
        return event

    def update_event(
        self, event_id: str, updated_event: dict[str, str], calendar_id: str = "primary"
    ) -> dict[str, str]:
        event = (
            self.service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=updated_event)
            .execute()
        )
        return event

    def search_events(
        self, start_time: str, end_time: str, calendar_id: str = "primary"
    ) -> list[dict[str, str]]:
        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_time,
                timeMax=end_time,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])


class GoogleCalendarEnv(Environment):
    def __init__(self, app_settings: dict, state: dict[str, list[dict]]) -> None:
        super().__init__(app_settings, state)
        token_path: str = self.app_settings["token_path"]
        self.service: GoogleCalendarService = GoogleCalendarService(
            token_path=token_path
        )
        self.events: dict = {}

    def execute(self, steps: list[dict]) -> bool:
        try:
            for step in steps:
                action: str
                params: dict
                for action, params in step.items():
                    match action:
                        case "create_and_cd_calendar":
                            calendar = self.service.create_calendar(params)
                            self.env_info["calendar_id"] = calendar["id"]
                        case "cd_calendar":
                            if params["id"] != "primary":
                                calendar = self.service.find_calendar_by_id(
                                    params["id"]
                                )
                                if calendar == {}:
                                    raise Exception(
                                        f"Calendar {params['id']} not found"
                                    )
                                self.env_info["calendar_id"] = calendar["id"]
                            else:
                                self.env_info["calendar_id"] = "primary"
                        case "clear_calendar":
                            self.service.clear_calendar(self.env_info["calendar_id"])
                        case "create_event":
                            event = self.service.create_event(
                                params.get("summary"),
                                params.get("location"),
                                params.get("description"),
                                params["start"]["dateTime"],
                                params["end"]["dateTime"],
                                params.get("attendees"),
                                self.env_info["calendar_id"],
                            )
                            self.events[event.get("id")] = event
                        case "delete_calendar":
                            self.service.delete_calendar(self.env_info["calendar_id"])
            return True
        except Exception as e:
            print(f"An error occurred in Google calendar env: {e}")
            return False

    def reset(self):
        self.execute(self.enter_steps)
        return self.env_info

    def __del__(self) -> None:
        if "calendar_id" in self.env_info and self.env_info["calendar_id"] != "primary":
            self.execute(self.exit_steps)
