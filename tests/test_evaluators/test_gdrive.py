# pytest -s tests/test_evaluators/test_gdrive.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {
                        "create_file": {
                            "path": "tmp/test.txt",
                            "content": "This is a test file.",
                        }
                    },
                ],
            },
            {
                "eval_type": "google_drive",
                "eval_procedure": [
                    {
                        "check_file_exists": {
                            "file_name": "Sample Document",
                            "content": "This is a test file.",
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_file": {"file_name": "Sample Document"}},
                    {
                        "upload_file": {
                            "name": "Sample Document",
                            "path": "tmp/test.txt",
                            "mime_type": "text/plain",
                        }
                    },
                ],
            },
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {"create_file": {"path": "tmp/sample.txt"}},
                ],
            },
            {
                "eval_type": "google_drive",
                "eval_procedure": [
                    {
                        "check_file_exists": {
                            "file_name": "Test Document",
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_file": {"file_name": "Test Document"}},
                    {
                        "upload_file": {
                            "name": "Test Document",
                            "path": "tmp/sample.txt",
                            "mime_type": "text/plain",
                        }
                    },
                ],
            },
        ]
    },
    {
        "evals": [
            {
                "eval_type": "filesystem",
                "reset_procedure": [
                    {"rmdir": {"path": "tmp"}},
                    {"mkdir": {"path": "tmp"}},
                    {
                        "create_file": {
                            "path": "tmp/test.txt",
                            "content": "This is a test file.",
                        }
                    },
                ],
            },
            {
                "eval_type": "google_drive",
                "eval_procedure": [
                    {
                        "check_folder_exists": {
                            "folder_name": "tmp",
                            "file_list": [{"name": "test.txt"}],
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_folder": {"folder_name": "tmp"}},
                    {
                        "create_folder": {
                            "folder_name": "tmp",
                            "file_list": [
                                {
                                    "name": "test.txt",
                                    "path": "tmp/test.txt",
                                    "mime_type": "text/plain",
                                }
                            ],
                        }
                    },
                ],
            },
        ]
    },
    {
        "evals": [
            {
                "eval_type": "google_drive",
                "eval_procedure": [
                    {
                        "check_folder_exists": {
                            "folder_name": "TestFolder",
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [{"delete_folder": {"folder_name": "TestFolder"}}],
            }
        ]
    },
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_gdrive(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
