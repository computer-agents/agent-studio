import os

from google.auth.transport.requests import Request
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class GoogleService(object):
    def __init__(
        self,
        scopes: list[str],
        token_path: str,
        service_name: str,
        service_version: str,
        debug: bool = False,
    ) -> None:
        self.scopes = scopes
        self.service_name = service_name
        self.service_version = service_version
        self.creds = self.authenticate(token_path)
        self.service = build(service_name, service_version, credentials=self.creds)
        self.debug = debug

    def authenticate(self, token_path: str) -> credentials.Credentials | None:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
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
                    f"{self.service_name}_credentials.json", self.scopes
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds
