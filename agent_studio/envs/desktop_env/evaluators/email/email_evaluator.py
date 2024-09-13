import filecmp
import logging
import os
import random
import shutil
from pathlib import Path

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
    reset_handler,
)
from agent_studio.utils.human_utils import confirm_action

logger = logging.getLogger(__name__)


def generate_random_email(from_address, to_address, subject, body):
    return {"from": from_address, "to": to_address, "subject": subject, "body": body}


# Sample data for random email generation
subjects = [
    "Project Update",
    "Meeting Reminder",
    "Your Order Confirmation",
    "Special Offer Just for You",
    "Invoice Attached",
    "Invitation to Webinar",
    "Weekly Report",
    "Monthly Newsletter",
    "Job Application",
    "Event Reminder",
    "Account Alert",
    "Password Reset",
    "Travel Itinerary",
    "Survey Request",
    "Your Subscription",
    "Re: Follow-up",
    "Congratulations!",
    "Thank You for Your Purchase",
    "New Features",
    "Security Update",
]

bodies = [
    "Please find attached the latest project update.",
    "Don't forget our meeting tomorrow at 10 AM.",
    "Thank you for your purchase! Your order has been confirmed.",
    "Enjoy an exclusive discount just for you!",
    "Attached is the invoice for your recent purchase.",
    "Join us for an upcoming webinar on cloud computing.",
    "Here is your weekly report summary.",
    "Check out the latest news and updates in this month's newsletter.",
    "We have received your job application and will get back to you shortly.",
    "This is a reminder for the event happening next week.",
    "We've detected unusual activity in your account. Please review immediately.",
    "Please click the link below to reset your password.",
    "Here is your travel itinerary for the upcoming trip.",
    "We would love to hear your feedback. Please take a moment to complete our survey.",
    "Your subscription has been successfully renewed.",
    "Following up on our previous conversation, please find the details attached.",
    "Congratulations! You've been selected for a special offer.",
    "Thank you for your recent purchase. We hope you enjoy it.",
    "Explore the new features we just added to your account.",
    "A security update is available. Please review the details.",
]

senders = [
    "no-reply@service.com",
    "support@company.com",
    "admin@newsletter.com",
    "sales@shop.com",
    "info@event.com",
    "alerts@bank.com",
    "notifications@social.com",
    "team@project.com",
    "hr@company.com",
    "user@example.com",
    "friend@example.com",
    "boss@example.com",
    "colleague@example.com",
    "client@example.com",
    "manager@example.com",
    "service@company.com",
]

inbox_emails = [
    # Emails for Automatic Classification and Archiving
    {
        "from": "admin@newsletter.com",
        "to": "user@example.com",
        "subject": "Monthly Newsletter",
        "body": "Here is your monthly newsletter.",
    },
    {
        "from": "boss@example.com",
        "to": "user@example.com",
        "subject": "Project Update",
        "body": "Please update the project plan.",
    },
    {
        "from": "sales@shop.com",
        "to": "user@example.com",
        "subject": "Congratulations! You've won a prize!",
        "body": "Claim your prize now.",
    },
    {
        "from": "alerts@bank.com",
        "to": "user@example.com",
        "subject": "Account Alert",
        "body": "Unusual activity detected.",
    },
    {
        "from": "billing@company.com",
        "to": "user@example.com",
        "subject": "Invoice Attached",
        "body": "Please find your invoice attached.",
    },
    # Emails for Spam Filtering
    {
        "from": "spam@phishing.com",
        "to": "user@example.com",
        "subject": "Special Offer Just for You",
        "body": "Exclusive deal available!",
    },
    {
        "from": "unknown@fake.com",
        "to": "user@example.com",
        "subject": "You've won a Prize!",
        "body": "Click here to claim.",
    },
    {
        "from": "no-reply@service.com",
        "to": "user@example.com",
        "subject": "Survey Request",
        "body": "Please take our survey.",
    },
    {
        "from": "spammer@offers.com",
        "to": "user@example.com",
        "subject": "Prize Winner!",
        "body": "You have been selected to win.",
    },
    {
        "from": "newsletter@ads.com",
        "to": "user@example.com",
        "subject": "Free Gift Inside",
        "body": "Open to receive your free gift.",
    },
    # Emails for Priority Sorting
    {
        "from": "boss@example.com",
        "to": "user@example.com",
        "subject": "Urgent: Meeting Tomorrow",
        "body": "Meeting at 9 AM.",
    },
    {
        "from": "manager@example.com",
        "to": "user@example.com",
        "subject": "Update Required",
        "body": "Please update the report.",
    },
    {
        "from": "alerts@bank.com",
        "to": "user@example.com",
        "subject": "Security Alert",
        "body": "Suspicious login detected.",
    },
    {
        "from": "team@project.com",
        "to": "user@example.com",
        "subject": "Project Update",
        "body": "Here is the project update.",
    },
    {
        "from": "hr@company.com",
        "to": "user@example.com",
        "subject": "Policy Update",
        "body": "New HR policies.",
    },
    # Emails for Automatic Reply/Send of Emails
    {
        "from": "friend@example.com",
        "to": "user@example.com",
        "subject": "Catch up soon?",
        "body": "Let's meet up next week.",
    },
    {
        "from": "client@example.com",
        "to": "user@example.com",
        "subject": "Follow-up on Proposal",
        "body": "Any updates on the proposal?",
    },
    {
        "from": "alerts@bank.com",
        "to": "user@example.com",
        "subject": "Account Alert",
        "body": "Please verify your recent activity.",
    },
    {
        "from": "newsletter@shopping.com",
        "to": "user@example.com",
        "subject": "Order Confirmation",
        "body": "Thank you for your purchase.",
    },
    {
        "from": "support@company.com",
        "to": "user@example.com",
        "subject": "Support Ticket Update",
        "body": "Your ticket has been updated.",
    },
    # Emails for Summarization and Refinement
    {
        "from": "team@project.com",
        "to": "user@example.com",
        "subject": "Weekly Report",
        "body": "Here is the weekly project report.",
    },
    {
        "from": "client@example.com",
        "to": "user@example.com",
        "subject": "Proposal Review",
        "body": "Please review the attached proposal.",
    },
    {
        "from": "hr@company.com",
        "to": "user@example.com",
        "subject": "HR Policy Update",
        "body": "New HR policy details attached.",
    },
    {
        "from": "boss@example.com",
        "to": "user@example.com",
        "subject": "Project Update",
        "body": "Please summarize the project status.",
    },
    {
        "from": "manager@example.com",
        "to": "user@example.com",
        "subject": "Leave Request",
        "body": "I would like to request leave for next month.",
    },
]


class EmailEvaluator(Evaluator):
    name: str = "email"

    def __init__(
        self,
        eval_procedure: list[dict],
        reset_procedure: list[dict],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )

    @staticmethod
    @evaluation_handler("exists")
    def exists(file_to_check: dict[str, bool]) -> None:
        for path, expected in file_to_check.items():
            path = os.path.expanduser(path)
            if expected != Path(path).exists():
                raise FeedbackException(
                    f"The error occurred when checking {path} existence. "
                    f"Expected: {expected}, but get: {not expected}"
                )

    @staticmethod
    @evaluation_handler("match_file")
    def match_file(file_to_check: dict[str, str]) -> None:
        for path, expected_path in file_to_check.items():
            path = os.path.expanduser(path)
            expected_path = os.path.expanduser(expected_path)
            if not filecmp.cmp(path, expected_path, shallow=False):
                raise FeedbackException(
                    f"The error occurred when checking {path}."
                    f"Expected: {expected_path}"
                )

    @staticmethod
    @reset_handler("rmdir")
    def rmdir(path: str) -> None:
        @confirm_action(f"Removing {path}")
        def _rmdir(path: str) -> None:
            if os.path.exists(path) and os.path.isdir(path):
                shutil.rmtree(path)
            logger.debug(f"{path} removed")

        path = os.path.expanduser(path)
        logger.debug(f"Removing {path}")
        _rmdir(path)

    @staticmethod
    @reset_handler("rename")
    def reset_mailbox(old_name: str, new_name: str) -> None:
        # Adding random emails to fill the inbox to 100 emails
        while len(inbox_emails) < 100:
            inbox_emails.append(
                {
                    "from": random.choice(senders),
                    "to": "user@example.com",
                    "subject": random.choice(subjects),
                    "body": random.choice(bodies),
                }
            )

        # sent_emails = [
        #     {
        #         "from": "user@example.com",
        #         "to": "boss@example.com",
        #         "subject": "Project Update",
        #         "body": "Here is the latest update on the project.",
        #     },
        #     {
        #         "from": "user@example.com",
        #         "to": "client@example.com",
        #         "subject": "Proposal Follow-up",
        #         "body": "Just following up on our last discussion.",
        #     },
        #     {
        #         "from": "user@example.com",
        #         "to": "friend@example.com",
        #         "subject": "Re: Catch up soon?",
        #         "body": "Sure, let's meet next week.",
        #     },
        #     {
        #         "from": "user@example.com",
        #         "to": "support@company.com",
        #         "subject": "Re: Support Ticket Update",
        #         "body": "Thanks for the update.",
        #     },
        #     {
        #         "from": "user@example.com",
        #         "to": "newsletter@shopping.com",
        #         "subject": "Order Confirmation",
        #         "body": "Thank you for the order details.",
        #     },
        #     # Adding more emails to fill the Sent folder to 20 emails
        #     *[
        #         generate_random_email(
        #             "user@example.com",
        #             random.choice(senders),
        #             random.choice(subjects),
        #             random.choice(bodies),
        #         )
        #         for _ in range(15)
        #     ],
        # ]

        # favorites_emails = [
        #     {
        #         "from": "boss@example.com",
        #         "to": "user@example.com",
        #         "subject": "Important: Project Deadline",
        #         "body": "Please ensure the project is completed on time.",
        #     },
        #     {
        #         "from": "client@example.com",
        #         "to": "user@example.com",
        #         "subject": "Feedback on Proposal",
        #         "body": "The proposal looks good, but we need some adjustments.",
        #     },
        #     {
        #         "from": "alerts@bank.com",
        #         "to": "user@example.com",
        #         "subject": "Account Security",
        #         "body": "Please verify your account security settings.",
        #     },
        #     {
        #         "from": "hr@company.com",
        #         "to": "user@example.com",
        #         "subject": "Salary Review",
        #         "body": "Your salary review is due next month.",
        #     },
        #     {
        #         "from": "team@project.com",
        #         "to": "user@example.com",
        #         "subject": "Team Meeting Notes",
        #         "body": "Here are the notes from our last meeting.",
        #     },
        #     # Adding more emails to fill the Favorites folder to 10 emails
        #     *[
        #         generate_random_email(
        #             random.choice(senders),
        #             "user@example.com",
        #             random.choice(subjects),
        #             random.choice(bodies),
        #         )
        #         for _ in range(5)
        #     ],
        # ]

        # recycle_bin_emails = [
        #     {
        #         "from": "spam@phishing.com",
        #         "to": "user@example.com",
        #         "subject": "You Have Won!",
        #         "body": "Claim your prize now!",
        #     },
        #     {
        #         "from": "unknown@scam.com",
        #         "to": "user@example.com",
        #         "subject": "Free Gift",
        #         "body": "Receive your free gift today.",
        #     },
        #     {
        #         "from": "sales@shop.com",
        #         "to": "user@example.com",
        #         "subject": "Special Offer Just for You",
        #         "body": "Exclusive deal available!",
        #     },
        #     # Adding more emails to fill the Recycle Bin to 15 emails
        #     *[
        #         generate_random_email(
        #             random.choice(senders),
        #             "user@example.com",
        #             random.choice(subjects),
        #             random.choice(bodies),
        #         )
        #         for _ in range(12)
        #     ],
        # ]
