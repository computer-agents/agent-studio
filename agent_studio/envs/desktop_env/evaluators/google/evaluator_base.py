from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
)


class GoogleEvaluatorBase(Evaluator):
    prompt: str = "evaluators/google/base_prompt"
