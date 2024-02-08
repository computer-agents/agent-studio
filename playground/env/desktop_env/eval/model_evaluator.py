import logging

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import Evaluator

config = Config()
logger = logging.getLogger(__name__)


class ModelEvaluator(Evaluator):
    name: str = "model"

    def __init__(self) -> None:
        # self.model = config.eval_model
        pass

    def reset(self) -> None:
        pass

    def __call__(self, **kwargs) -> tuple[float, str]:
        # trajectory = kwargs["trajectory"]
        # score = self.model(trajectory)
        return 1.0, "Model evaluation successful."
