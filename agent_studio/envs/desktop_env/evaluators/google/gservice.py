import json
import logging
import os

from google.auth import exceptions
from google.auth.transport.requests import Request
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from agent_studio.config import Config

config = Config()
logger = logging.getLogger(__name__)


class GoogleService(object):
    def __init__(
        self,
        scopes: list[str],
        service_name: str,
        service_version: str,
        debug: bool = False,
    ) -> None:
        self.scopes = scopes
        self.service_name = service_name
        self.service_version = service_version
        self.creds = self.authenticate(config.google_credential_path)
        self.service = build(service_name, service_version, credentials=self.creds)
        self.debug = debug

    def authenticate(self, credential_path: str) -> credentials.Credentials | None:
        token_path = os.path.join(
            os.path.dirname(credential_path), f"{self.service_name}_token.json"
        )
        with open(credential_path, "r") as f:
            credential = json.loads(f.read())
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                token = json.loads(f.read())
        else:
            token = None
        try:
            creds = self.update_token_crediential(credential, token)
        except exceptions.RefreshError:
            creds = self.update_token_crediential(credential, None)
        if creds is None:
            logger.error("Failed to authenticate")
            raise Exception("Failed to authenticate")
        else:
            if token != json.loads(creds.to_json()):
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
        return creds

    def update_token_crediential(
        self, credential: dict, token: dict | None
    ) -> credentials.Credentials | None:
        creds = None
        if token is not None:
            creds = credentials.Credentials.from_authorized_user_info(
                token, self.scopes
            )
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(credential, self.scopes)
                creds = flow.run_local_server(port=0)
        return creds
