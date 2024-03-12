# pytest -s tests/test_evaluators/test_joint_evaluation.py
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
                                "start": {"dateTime": "2024-01-05T11:00:00+01:00"},
                                "end": {"dateTime": "2024-01-05T12:00:00+01:00"},
                            },
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {"clear_calendar": {}},
                    {
                        "create_event": {
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
            },
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
                        "permissions_check": {
                            "file_to_check": {
                                "tmp/test.txt": "-rw-r--r--",
                                "tmp": "drwxrwxr-x",
                            }
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
                    {"chmod": {"path": "tmp/test.txt", "mode": "0o644"}},
                    {"chmod": {"path": "tmp", "mode": "0o775"}},
                ],
            },
        ]
    }
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_joint(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
