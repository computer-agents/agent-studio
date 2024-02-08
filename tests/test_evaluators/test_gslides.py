# pytest -s tests/test_evaluators/test_gslides.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

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


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_gslides(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score = comb()
    assert score == 1.0
