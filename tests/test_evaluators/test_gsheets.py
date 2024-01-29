# pytest -s tests/test_evaluators/test_gsheets.py
from playground.desktop_env.eval.evaluator_helper import evaluator_router

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


def test_gsheets():
    for task_config in TASK_CONFIGS:
        comb = evaluator_router(task_config)
        comb.reset()
        score = comb()
        assert score == 1.0
