# pytest -s tests/test_evaluators/test_qa.py
from playground.desktop_env.eval.evaluator_helper import evaluator_router

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


def test_qa():
    for task_config in TASK_CONFIGS:
        comb = evaluator_router(task_config)
        comb.reset()
        score = comb(
            **{
                "response": task_config["evals"][0]["eval_procedure"][0][
                    "string_match"
                ]["answer"]
            }
        )
        assert score == 1.0
