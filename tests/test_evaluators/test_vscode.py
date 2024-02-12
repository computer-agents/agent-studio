# pytest -s tests/test_evaluators/test_vscode.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "vscode",
                "eval_procedure": [
                    {
                        "extension_installed": {
                            "extension_id": "DavidAnson.vscode-markdownlint",
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "uninstall_extension": {
                            "extension_id": "DavidAnson.vscode-markdownlint"
                        }
                    },
                    {
                        "install_extension": {
                            "extension_id": "DavidAnson.vscode-markdownlint"
                        }
                    },
                ],
            }
        ],
    },
    {
        "evals": [
            {
                "eval_type": "vscode",
                "eval_procedure": [
                    {"most_installed_extension": {"keyword": "Markdown"}}
                ],
                "reset_procedure": [
                    {
                        "uninstall_extension": {
                            "extension_id": "esbenp.prettier-vscode"
                        },
                        "install_extension": {"extension_id": "esbenp.prettier-vscode"},
                    }
                ],
            }
        ],
    },
    {
        "evals": [
            {
                "eval_type": "vscode",
                "eval_procedure": [
                    {
                        "extension_installed": {
                            "extension_id": "DavidAnson.vscode-markdownlint",
                            "version": "0.49.0",
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "uninstall_extension": {
                            "extension_id": "DavidAnson.vscode-markdownlint"
                        },
                        "install_extension": {
                            "extension_id": "DavidAnson.vscode-markdownlint@0.49.0"
                        },
                    }
                ],
            }
        ],
    },
    {
        "evals": [
            {
                "eval_type": "vscode",
                "eval_procedure": [
                    {
                        "extension_installed": {
                            "extension_id": "DavidAnson.vscode-markdownlint",
                            "exists": True,
                            "published_before": "2023-01-01T00:00:00Z",
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "uninstall_extension": {
                            "extension_id": "DavidAnson.vscode-markdownlint"
                        },
                        "install_extension": {
                            "extension_id": "DavidAnson.vscode-markdownlint@0.47.0"
                        },
                    }
                ],
            }
        ],
    },
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_vscode(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
