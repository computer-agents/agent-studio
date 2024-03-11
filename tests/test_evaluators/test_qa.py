# pytest -s tests/test_evaluators/test_qa.py
import pytest

from agent_studio.envs.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "qa",
                "eval_procedure": [{"string_match": {"answer": "Document"}}],
            }
        ]
    }
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_qa(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb(
        **{
            "response": task_config["evals"][0]["eval_procedure"][0]["string_match"][
                "answer"
            ]
        }
    )
    assert score == 1.0, feedback
