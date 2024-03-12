# pytest -s tests/test_evaluators/test_gsheets.py
import pytest

from agent_studio.envs.desktop_env.evaluators.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "google_sheets",
                "eval_procedure": [
                    {
                        "check_spreadsheet_exists": {
                            "title": "Sample Spreadsheet",
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_spreadsheet": {"title": "Sample Spreadsheet"}},
                    {"create_spreadsheet": {"title": "Sample Spreadsheet"}},
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "google_sheets",
                "eval_procedure": [
                    {
                        "check_spreadsheet_exists": {
                            "title": "Sample Spreadsheet",
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_spreadsheet": {"title": "Sample Spreadsheet"}}
                ],
            }
        ]
    },
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_gsheets(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
