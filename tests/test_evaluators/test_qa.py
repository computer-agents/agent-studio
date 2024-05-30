# pytest -s tests/test_evaluators/test_qa.py
import pytest

from agent_studio.envs.desktop_env.evaluators.evaluator_helper import evaluator_router

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
    trajectory = [
        {"role": "system", "content": "System prompt"},
        {"role": "assistant", "content": "[[[Document]]]"},
    ]
    score, feedback = comb(
        trajectory=trajectory,
    )
    assert score == 1.0, feedback
