# pytest -s tests/test_evaluators/test_filesystem.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [
                    {
                        "exists": {
                            "file_to_check": {"tmp/test.txt": True, "tmp": True}
                        },
                        "type_check": {
                            "file_to_check": {"tmp/test.txt": "file", "tmp": "folder"}
                        },
                        "permissions_check": {
                            "file_to_check": {
                                "tmp/test.txt": "-rw-r--r--",
                                "tmp": "0o775",
                            }
                        },
                        "content_check": {
                            "file_to_check": {"tmp/test.txt": "Hello World!"}
                        },
                    }
                ],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {
                        "create_file": {
                            "path": "tmp/test.txt",
                            "content": "Hello World!",
                        }
                    },
                    {"chmod": {"path": "tmp", "mode": "0o775"}},
                    {"chmod": {"path": "tmp/test.txt", "mode": "0o644"}},
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [
                    {
                        "exists": {"file_to_check": {"tmp": True}},
                        "type_check": {"file_to_check": {"tmp": "folder"}},
                    }
                ],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {"create_file": {"path": "tmp/test.txt"}},
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [{"exists": {"file_to_check": {"tmp": False}}}],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {"rmdir": {"path": "tmp"}},
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [
                    {"exists": {"file_to_check": {"tmp/test.txt": True, "tmp": True}}},
                    {
                        "type_check": {
                            "file_to_check": {"tmp/test.txt": "file", "tmp": "folder"}
                        }
                    },
                    {
                        "content_check": {
                            "file_to_check": {"tmp/test.txt": "Hello World!"}
                        }
                    },
                ],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {
                        "create_file": {
                            "path": "tmp/test.txt",
                            "content": "Hello World!",
                        }
                    },
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [
                    {"exists": {"file_to_check": {"tmp/calendar.txt": True}}},
                    {"type_check": {"file_to_check": {"tmp/calendar.txt": "file"}}},
                    {
                        "content_check": {
                            "file_to_check": {"tmp/calendar.txt": "Meeting with Team\n"}
                        }
                    },
                ],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {
                        "create_file": {
                            "path": "tmp/calendar.txt",
                            "content": "Meeting with Team\n",
                        }
                    },
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [
                    {
                        "exists": {
                            "file_to_check": {
                                "tmp/Meeting_Summaries/Budget_Review_Summary_20240415.txt": True  # noqa: E501
                            }
                        }
                    },
                    {
                        "content_check": {
                            "file_to_check": {
                                "tmp/Meeting_Summaries/Budget_Review_Summary_20240415.txt": "Summary of Budget Review meeting on 2024-04-15"  # noqa: E501
                            }
                        }
                    },
                ],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp/Meeting_Summaries"}},
                    {
                        "create_file": {
                            "path": "tmp/Meeting_Summaries/Budget_Review_Summary_20240415.txt",  # noqa: E501
                            "content": "Summary of Budget Review meeting on 2024-04-15",
                        }
                    },
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "eval_procedure": [
                    {
                        "exists": {
                            "file_to_check": {
                                "tmp/Notifications/Team_Sync_Rescheduled_20240512.txt": True  # noqa: E501
                            }
                        }
                    },
                    {
                        "type_check": {
                            "file_to_check": {
                                "tmp/Notifications/Team_Sync_Rescheduled_20240512.txt": "file"  # noqa: E501
                            }
                        }
                    },
                    {
                        "content_check": {
                            "file_to_check": {
                                "tmp/Notifications/Team_Sync_Rescheduled_20240512.txt": "Team Sync meeting has been rescheduled to 2024-05-12 at 2:00 PM"  # noqa: E501
                            }
                        }
                    },
                ],
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp/Notifications"}},
                    {
                        "create_file": {
                            "path": "tmp/Notifications/Team_Sync_Rescheduled_20240512.txt",  # noqa: E501
                            "content": "Team Sync meeting has been rescheduled to 2024-05-12 at 2:00 PM",  # noqa: E501
                        }
                    },
                ],
            }
        ]
    },
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_filesystem(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
