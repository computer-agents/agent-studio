# pytest -s tests/test_evaluators/test_gmail.py
import pytest

from agent_studio.envs.desktop_env.evaluators.evaluator_helper import evaluator_router

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
                        "is_email_marked_important": {
                            "message_info": {
                                "subject": "Automated Email",
                                "body": "This is automatically sent message",
                            },
                            "gt": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "mark_message_important": {
                            "is_important": True,
                            "subject_contains": "Automated Email",
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
                        "is_email_in_trash": {
                            "in_trash": True,
                            "message_info": {
                                "subject": "Automated travel plan",
                                "body_contains": "automatically"
                            }
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "add_email_to_trash": {
                            "message_info": {
                                "subject": "Automated travel plan",
                                "body": "This is automatically sent message"
                            }
                        }
                    }
                ]
            }
        ],
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
    score, feedback = comb()
    assert score == 1.0, feedback

test_gmail(TASK_CONFIGS[0])
test_gmail(TASK_CONFIGS[1])
test_gmail(TASK_CONFIGS[2])
test_gmail(TASK_CONFIGS[3])
test_gmail(TASK_CONFIGS[4])
test_gmail(TASK_CONFIGS[5])
test_gmail(TASK_CONFIGS[6])
test_gmail(TASK_CONFIGS[7])
