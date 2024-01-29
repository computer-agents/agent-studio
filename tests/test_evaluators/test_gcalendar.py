# pytest -s tests/test_evaluators/test_gcalendar.py
from playground.desktop_env.eval.evaluator_helper import evaluator_router

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
                            "exists": True,
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
                                "summary": "Follow-up Meeting",
                                "location": "Conference Room",
                                "description": "Discuss action points from last meeting",  # noqa: E501
                                "start": {"dateTime": "2024-03-08T10:00:00Z"},
                                "end": {"dateTime": "2024-03-08T11:00:00Z"},
                            },
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Follow-up Meeting",
                                "location": "Conference Room",
                                "description": "Discuss action points from last meeting",  # noqa: E501
                                "start": {"dateTime": "2024-03-08T10:00:00Z"},
                                "end": {"dateTime": "2024-03-08T11:00:00Z"},
                            }
                        }
                    },
                    {
                        "create_event": {
                            "event_info": {
                                "summary": "Follow-up Meeting",
                                "location": "Conference Room",
                                "description": "Discuss action points from last meeting",  # noqa: E501
                                "start": {
                                    "dateTime": "2024-03-08T10:00:00Z",
                                    "timezone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2024-03-08T11:00:00Z",
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
                                "summary": "Budget Review Follow-up",
                                "description": "Reminder to prepare for the follow-up meeting",  # noqa: E501
                                "start": {"dateTime": "2024-04-22T09:00:00Z"},
                                "end": {"dateTime": "2024-04-22T09:30:00Z"},
                            },
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Budget Review Follow-up",
                                "description": "Reminder to prepare for the follow-up meeting",  # noqa: E501
                                "start": {"dateTime": "2024-04-22T09:00:00Z"},
                                "end": {"dateTime": "2024-04-22T09:30:00Z"},
                            }
                        }
                    },
                    {
                        "create_event": {
                            "event_info": {
                                "summary": "Budget Review Follow-up",
                                "description": "Reminder to prepare for the follow-up meeting",  # noqa: E501
                                "start": {
                                    "dateTime": "2024-04-22T09:00:00Z",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2024-04-22T09:30:00Z",
                                    "timeZone": "UTC",
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
                                "summary": "Team Sync",
                                "start": {"dateTime": "2024-05-12T14:00:00Z"},
                                "end": {"dateTime": "2024-05-12T15:00:00Z"},
                            },
                            "exists": True,
                        }
                    },
                    {
                        "check_event_exists": {
                            "event_info": {
                                "summary": "Team Sync",
                                "start": {"dateTime": "2024-05-10T00:00:00Z"},
                            },
                            "exists": False,
                        }
                    },
                ],
                "reset_procedure": [
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Team Sync",
                                "start": {"dateTime": "2024-05-12T14:00:00Z"},
                                "end": {"dateTime": "2024-05-12T15:00:00Z"},
                            }
                        }
                    },
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Team Sync",
                                "start": {"dateTime": "2024-05-10T00:00:00Z"},
                                "end": {"dateTime": "2024-05-10T01:00:00Z"},
                            }
                        }
                    },
                    {
                        "create_event": {
                            "event_info": {
                                "summary": "Team Sync",
                                "start": {
                                    "dateTime": "2024-05-10T00:00:00Z",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2024-05-10T01:00:00Z",
                                    "timeZone": "UTC",
                                },
                                "attendees": [],
                            }
                        }
                    },
                    {
                        "create_event": {
                            "event_info": {
                                "summary": "Team Sync",
                                "start": {
                                    "dateTime": "2024-05-12T14:00:00Z",
                                    "timeZone": "UTC",
                                },
                                "end": {
                                    "dateTime": "2024-05-12T15:00:00Z",
                                    "timeZone": "UTC",
                                },
                                "attendees": [],
                            }
                        }
                    },
                    {
                        "delete_event": {
                            "event_info": {
                                "summary": "Team Sync",
                                "start": {"dateTime": "2024-05-10T00:00:00Z"},
                                "end": {"dateTime": "2024-05-10T01:00:00Z"},
                            }
                        }
                    },
                ],
            }
        ]
    },
]


def test_calendar():
    for task_config in TASK_CONFIGS:
        comb = evaluator_router(task_config)
        comb.reset()
        score = comb()
        assert score == 1.0
