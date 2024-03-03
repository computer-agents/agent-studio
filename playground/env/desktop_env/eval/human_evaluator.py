import logging

from playground.config import Config
from playground.env.desktop_env.eval.evaluator import Evaluator
from playground.utils.task_status import StateEnum, StateInfo, TaskStatus

from playground.env.desktop_env.eval.evaluator import (
    evaluation_handler,
    FeedbackException,
)

logger = logging.getLogger(__name__)
task_status = TaskStatus()
config = Config()


class HumanEvaluator(Evaluator):
    name: str = "human"

    @evaluation_handler("human")
    def handle_human_evaluation(self) -> None:
        """Human evaluation handler."""
        if config.headless:
            score = float(input("Is the task successful? (y/n): ") == "y")
            if score == 0:
                feedback = input(
                    "Type any feedback and press Enter (or press Enter to skip): "
                )
                raise FeedbackException(feedback)
        else:
            task_status.set_task_state(
                StateInfo(
                    state=StateEnum.WAIT_FOR_INPUT,
                    message="Is the task successful? (y/n): ",
                )
            )
            state = task_status.wait_for_state_change(StateEnum.WAIT_FOR_INPUT)
            assert state.state == StateEnum.IN_PROGRESS, state
            if state.message != "y":
                task_status.set_task_state(
                    StateInfo(
                        state=StateEnum.WAIT_FOR_INPUT,
                        message="Type any feedback and press Enter (or press Enter to skip): ",  # noqa: E501
                    )
                )
                state = task_status.wait_for_state_change(StateEnum.WAIT_FOR_INPUT)
                assert state.state == StateEnum.IN_PROGRESS, state
                assert isinstance(state.message, str), state
                feedback = state.message
                raise FeedbackException(feedback)
