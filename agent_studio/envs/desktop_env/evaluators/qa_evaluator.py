import logging
import re
from typing import Any

from agent_studio.agent.base_agent import TrajectorySeg
from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
)

logger = logging.getLogger(__name__)

config = Config()


class QAEvaluator(Evaluator):
    name: str = "qa"

    def __init__(
        self,
        eval_procedure: list[dict[str, dict[str, Any]]],
        reset_procedure: list[dict[str, dict[str, Any]]],
    ) -> None:
        super().__init__(
            eval_procedure=eval_procedure,
            reset_procedure=reset_procedure,
        )

    @evaluation_handler("string_match")
    def string_match(self, trajectory: list[TrajectorySeg], answer: str) -> None:
        logging.info(
            f"[QA Evaluator] Evaluating string match with params: {trajectory},"
            "{answer}"
        )
        if not trajectory:
            raise FeedbackException("The trajectory is empty.")
        agent_response: str | None = trajectory[-1].response
        if agent_response is None:
            raise FeedbackException(
                f"Could not find the answer in the trajectory: {trajectory}."
            )
        pattern = re.compile(config.qa_answer_pattern)
        matched: re.Match[str] | None = pattern.search(agent_response)
        if matched is None:
            raise FeedbackException(
                f"Could not find the answer in the trajectory: {trajectory}."
            )
        agent_answer = matched.group(1)  # Cast agent_answer to re.Match[str]
        if agent_answer != answer:
            raise FeedbackException(
                f"The answer is incorrect: {agent_answer}. Expected: {answer}."
            )
