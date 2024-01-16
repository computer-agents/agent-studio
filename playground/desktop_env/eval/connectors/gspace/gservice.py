import os

from google.auth.transport.requests import Request
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from playground.config import Config

config = Config()


class GoogleService(object):
    def __init__(
        self,
        scopes: list[str],
        service_name: str,
        service_version: str,
        debug: bool = False,
    ) -> None:
        self.scopes = scopes
        # "https://www.googleapis.com/auth/calendar",
        # "https://www.googleapis.com/auth/documents",
        # "https://www.googleapis.com/auth/presentations",
        # "https://www.googleapis.com/auth/spreadsheets",
        # "https://www.googleapis.com/auth/drive",
        # "https://www.googleapis.com/auth/gmail.compose",
        # "https://www.googleapis.com/auth/gmail.readonly",
        # "https://www.googleapis.com/auth/gmail.send",
        # "https://www.googleapis.com/auth/gmail.labels",
        # "https://www.googleapis.com/auth/gmail.settings.basic",
        # "https://www.googleapis.com/auth/gmail.settings.sharing",
        # "https://mail.google.com/",
        # "https://www.googleapis.com/auth/classroom.courses",
        # "https://www.googleapis.com/auth/contacts",
        # "https://www.googleapis.com/auth/tasks",
        # "https://www.googleapis.com/auth/userinfo.profile",
        # "https://www.googleapis.com/auth/userinfo.email",
        # "https://www.googleapis.com/auth/photoslibrary",
        self.service_name = service_name
        self.service_version = service_version
        self.creds = self.authenticate(config.google_credential_path)
        self.service = build(service_name, service_version, credentials=self.creds)
        self.debug = debug

    def authenticate(self, credential_path: str) -> credentials.Credentials | None:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        token_path = os.path.join(
            os.path.dirname(credential_path), f"{self.service_name}_token.json"
        )
        if os.path.exists(token_path):
            creds = credentials.Credentials.from_authorized_user_file(
                token_path, self.scopes
            )
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credential_path,
                    self.scopes,
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds
