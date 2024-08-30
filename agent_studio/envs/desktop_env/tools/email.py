import requests


class Email:
    def __init__(self, base_url="http://localhost:8025"):
        self.base_url = base_url

    def get_message_by_id(self, message_id: str):
        """Fetches the details of a specific email by ID.

        Args:
            message_id (str): The ID of the email to fetch.

        Returns:
            dict: A dictionary containing the email details.
        """
        response = requests.get(f"{self.base_url}/api/v2/messages/{message_id}")
        response.raise_for_status()
        return response.json()

    def delete_message_by_id(self, message_id: str):
        """Deletes a specific email by ID.

        Args:
            message_id (str): The ID of the email to delete.
        """
        response = requests.delete(f"{self.base_url}/api/v1/messages/{message_id}")
        response.raise_for_status()

    def get_all_messages(self):
        """Fetches all emails from the MailHog instance.

        Returns:
            dict: A dictionary containing the messages.
        """
        response = requests.get(f"{self.base_url}/api/v2/messages")
        response.raise_for_status()
        return response.json()

    def delete_all_messages(self):
        """Deletes all emails in the MailHog instance."""
        response = requests.delete(f"{self.base_url}/api/v1/messages")
        response.raise_for_status()

    def send_email(self, from_address: str, to_address: str, subject: str, body: str):
        """Sends an email using MailHog's SMTP server.

        Args:
            from_address (str): The sender's email address.
            to_address (str): The recipient's email address.
            subject (str): The subject of the email.
            body (str): The body of the email.
        """
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = from_address
        msg["To"] = to_address

        smtp_server = "localhost"
        smtp_port = 1025

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.sendmail(from_address, [to_address], msg.as_string())

    def search_messages(
        self, kind: str = "containing", limit: int = 50, start: str = "", end: str = ""
    ):
        """Searches for messages based on criteria.

        Args:
            kind (str): The type of search (e.g., 'containing').
            limit (int): The number of messages to return.
            start (str): The start time for the search.
            end (str): The end time for the search.

        Returns:
            dict: A dictionary containing the search results.
        """
        params = {"kind": kind, "limit": limit, "start": start, "end": end}
        response = requests.get(f"{self.base_url}/api/v2/messages", params=params)
        response.raise_for_status()
        return response.json()

    def initialize_mailbox(self, inbox_emails: list):
        """Initializes the mailbox by clearing all existing emails and
        sending predefined emails."""
        self.delete_all_messages()
        for email in inbox_emails:
            self.send_email(email["from"], email["to"], email["subject"], email["body"])
