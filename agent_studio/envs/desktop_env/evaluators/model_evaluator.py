import logging

from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
)
from agent_studio.llm import ModelManager

logger = logging.getLogger(__name__)
model_manager = ModelManager()


class ModelEvaluator(Evaluator):
    name: str = "model"

    @evaluation_handler("model_evaluation")
    def handle_model_evaluation(self, ) -> None:
        pass
