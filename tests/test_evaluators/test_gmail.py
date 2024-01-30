# pytest -s tests/test_evaluators/test_gmail.py
import pytest

from playground.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_draft_exists": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_draft": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                            }
                        }
                    }
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_draft_exists": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                            },
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "create_draft": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                            }
                        }
                    }
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_draft_exists": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_draft": {
                            "draft_info": {
                                "subject": "Automated draft",
                                "recipient": "gduser@workspacesamples.dev",
                                "body": "This is automated draft mail",
                            }
                        }
                    }
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_sent_message_exists": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_sent_message": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            }
                        }
                    }
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_sent_message_exists": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            },
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "send_message": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            }
                        }
                    }
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "gmail",
                "eval_procedure": [
                    {
                        "check_sent_message_exists": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_sent_message": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            }
                        }
                    }
                ],
            }
        ]
    },
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_gmail(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score = comb()
    assert score == 1.0
