# pytest -s tests/test_evaluators/test_gcalendar.py
import pytest

from agent_studio.envs.desktop_env.evaluators.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "google_calendar",
                "eval_procedure": [
                    {
                        "check_event_exists": {
                            "event_info": {
                                "summary": "Meeting with Team",
                                "location": "Office",
                                "description": "Discuss project status",
                                "start": {"dateTime": "2024-01-05T10:00:00Z"},
                                "end": {"dateTime": "2024-01-05T11:00:00Z"},
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Meeting with Team",
                                "location": "Office",
                                "description": "Discuss project status",
                                "start": {"dateTime": "2024-01-05T10:00:00Z"},
                                "end": {"dateTime": "2024-01-05T11:00:00Z"},
                            }
                        }
                    },
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "google_calendar",
                "eval_procedure": [
                    {
                        "check_event_exists": {
                            "event_info": {
                                "summary": "Meeting with Team",
                                "location": "Office",
                                "description": "Discuss project status",
                                "start": {"dateTime": "2024-01-05T10:00:00Z"},
                                "end": {"dateTime": "2024-01-05T11:00:00Z"},
                                "attendees": [{"email": "ceo@example.com"}],
                            },
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "create_event": {
                            "event_info": {
                                "summary": "Meeting with Team",
                                "location": "Office",
                                "description": "Discuss project status",
                                "start": {
                                    "dateTime": "2024-01-05T10:00:00Z",
                                    "timezone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2024-01-05T11:00:00Z",
                                    "timezone": "UTC",
                                },
                                "colorId": "11",
                                "reminders": {
                                    "useDefault": False,
                                    "overrides": [{"method": "email", "minutes": 60}],
                                },
                                "attendees": [{"email": "ceo@example.com"}],
                            }
                        }
                    },
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "google_calendar",
                "eval_procedure": [
                    {
                        "check_event_exists": {
                            "event_info": {
                                "summary": "Meeting with Team",
                                "location": "Office",
                                "description": "Discuss project status",
                                "start": {"dateTime": "2024-01-05T10:00:00Z"},
                                "end": {"dateTime": "2024-01-05T11:00:00Z"},
                                "attendees": [{"email": "ceo@example.com"}],
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Meeting with Team",
                                "location": "Office",
                                "description": "Discuss project status",
                                "start": {"dateTime": "2024-01-05T10:00:00Z"},
                                "end": {"dateTime": "2024-01-05T11:00:00Z"},
                                "colorId": "11",
                                "reminders": {
                                    "useDefault": False,
                                    "overrides": [{"method": "email", "minutes": 60}],
                                },
                            }
                        }
                    },
                ],
            }
        ]
    },
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_calendar(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
