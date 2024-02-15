# pytest -s tests/test_evaluators/test_gforms.py
import pytest

from playground.env.desktop_env.eval.evaluator_helper import evaluator_router

FORM_TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "google_forms",
                "eval_procedure": [
                    {
                        "check_form_exists": {
                            "form_info": {
                                "title": "Sample Form",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_form": {
                            "form_info": {
                                "title": "Sample Form",
                            }
                        }
                    },
                ],
            }
        ]
    },
    # {
    #     "evals": [
    #         {
    #             "eval_type": "google_forms",
    #             "eval_procedure": [
    #                 {
    #                     "check_form_exists": {
    #                         "form_info": {
    #                             "title": "Sample Form",
    #                         },
    #                         "exists": True,
    #                     }
    #                 }
    #             ],
    #             "reset_procedure": [
    #                 {
    #                     "create_form": {
    #                         "form_info": {
    #                             "title": "Sample Form",
    #                         }
    #                     }
    #                 },
    #             ],
    #         }
    #     ]
    # },
    {
        "evals": [
            {
                "eval_type": "google_forms",
                "eval_procedure": [
                    {
                        "check_form_exists": {
                            "form_info": {
                                "title": "Sample Form",
                            },
                            "exists": False,
                        }
                    }
                ],
                "reset_procedure": [
                    {
                        "delete_form": {
                            "form_info": {
                                "title": "Sample Form",
                            }
                        }
                    },
                ],
            }
        ]
    },
]


@pytest.mark.parametrize("task_config", FORM_TASK_CONFIGS)
def test_gforms(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback
