# pytest -s tests/test_evaluators/test_telegram.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "telegram",
                "eval_procedure": [
                    {
                        "message_match": {
                            "chat_id": "me",
                            "ref_messages": [
                                {
                                    "type": "text",
                                    "compare_method": "exact",
                                    "value": "hi",
                                },
                                {
                                    "type": "text",
                                    "compare_method": "exact",
                                    "value": "Welcome to the playground!",
                                },
                                {
                                    "type": "document",
                                    "file_path": "playground_data/test/"
                                    "telegram/GitHub-logo.png",
                                    "caption": "GitHub logo.",
                                    "replyto": {
                                        "type": "text",
                                        "compare_method": "exact",
                                        "value": "hi",
                                    },
                                },
                            ],
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_recent_messages": {"chat_id": "me", "n": 3}},
                    {
                        "send_messages": {
                            "chat_id": "me",
                            "messages": ["hi", "Welcome to the playground!"],
                        }
                    },
                    {
                        "send_document": {
                            "chat_id": "me",
                            "replyto_offset": 1,
                            "file_path": "playground_data/test"
                            "/telegram/GitHub-logo.png",
                            "caption": "GitHub logo.",
                        }
                    },
                ],
            }
        ]
    }
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_telegram(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
