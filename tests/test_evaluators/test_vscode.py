# pytest -s tests/test_evaluators/test_vscode.py
from playground.desktop_env.eval.evaluator_helper import evaluator_router

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


def test_vscode():
    for task_config in TASK_CONFIGS:
        comb = evaluator_router(task_config)
        comb.reset()
        score = comb()
        assert score == 1.0
