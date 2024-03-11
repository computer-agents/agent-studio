# pytest -s tests/test_evaluators/test_process.py
import pytest

from agent_studio.envs.desktop_env.eval.evaluator_helper import evaluator_router

TASK_CONFIGS = [
    {
        "evals": [
            {
                "eval_type": "process",
                "eval_procedure": [
                    {
                        "match_process": {"name": "(?<!\\w)(?i:code)(?!\\w)"},
                    }
                ],
                "reset_procedure": [
                    {
                        "pkill_by_name": {"name": "(?<!\\w)(?i:code)(?!\\w)"},
                        "create_process": {
                            "cmd": ["code"],
                            "wait_for": "(?<!\\w)(?i:code)(?!\\w)",
                        },
                    }
                ],
            }
        ]
    }
]


@pytest.mark.parametrize("task_config", TASK_CONFIGS)
def test_process(task_config):
    comb = evaluator_router(task_config)
    comb.reset()
    score, feedback = comb()
    assert score == 1.0, feedback


if __name__ == "__main__":
    test_process(TASK_CONFIGS[0])
