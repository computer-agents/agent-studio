# pytest -s tests/test_evaluators/test_gslides.py
from playground.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "google_slides",
                "eval_procedure": [
                    {
                        "check_presentation_exists": {
                            "title": "Sample Presentation",
                            "exists": True,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_presentation": {"title": "Sample Presentation"}},
                    {"create_presentation": {"title": "Sample Presentation"}},
                ],
            }
        ]
    },
    {
        "evals": [
            {
                "eval_type": "google_slides",
                "eval_procedure": [
                    {
                        "check_presentation_exists": {
                            "title": "Sample Presentation",
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {"delete_presentation": {"title": "Sample Presentation"}}
                ],
            }
        ]
    },
]


def test_gslides():
    for task_config in TASK_CONFIGS:
        comb = evaluator_router(task_config)
        comb.reset()
        score = comb()
        assert score == 1.0
