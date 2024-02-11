# pytest -s tests/test_evaluators/test_gcalendar.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

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
                                "attendees": [],
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
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_calendar(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score = comb()
    assert score[0] == 1.0
