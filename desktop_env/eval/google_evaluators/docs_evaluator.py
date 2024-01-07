import json
import os.path
import os

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from desktop_env.eval.evaluator import Evaluator


class GoogleDocsEvaluator(Evaluator):
    @staticmethod
    def string_match(ref: str, pred: str) -> float:
        return float(pred == ref)

    @staticmethod
    def get_text_at_index(document, index: int):
        for element in document["body"]["content"]:
            if "startIndex" in element and "endIndex" in element:
                if element["startIndex"] <= index < element["endIndex"]:
                    # Assuming the element contains text
                    if "textRun" in element["paragraph"]["elements"][0]:
                        return element["paragraph"]["elements"][0]["textRun"]["content"]
        return None

    def __call__(
        self,
        config_file: Path | str,
    ) -> float:
        with open(config_file, "r") as f:
            configs = json.load(f)

        # score = 1.0
        # document = configs["eval"]["document"]
        # index = configs["eval"]["index"]
        # for approach, value in configs["eval"]["reference_answers"].items():
        #     match approach:
        #         case "string_match":
        #             pred = GoogleDocsEvaluator.get_text_at_index(document, index)
        #             score *= self.string_match(ref=value, pred=pred)

        # return score


if __name__ == "__main__":
    # If modifying these scopes, delete the file token.json.
    scopes = ["https://www.googleapis.com/auth/documents.readonly"]

    # The ID of the document.
    document_id = "1HgxPOboJFd8RYxODbQbb5jtM3Hxc1Y9OyO94SNJ4qkE"

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
            creds = flow.run_local_server(port=51152)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("docs", "v1", credentials=creds)

        # Retrieve the documents contents from the Docs service.
        document = service.documents().get(documentId=document_id).execute()
        print(f"The title of the document is: {document.get('title')}")

        # Get text at a specific index
        index = 10
        text_at_index = GoogleDocsEvaluator.get_text_at_index(document, index)
        print(f"The text:", text_at_index)

    except HttpError as err:
        print(err)
