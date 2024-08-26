import logging

from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator import (
    Evaluator,
    FeedbackException,
    evaluation_handler,
)
from agent_studio.utils.task_status import StateEnum, StateInfo, TaskStatus

logger = logging.getLogger(__name__)
task_status = TaskStatus()
config = Config()


class HumanEvaluator(Evaluator):
    name: str = "human"

    @evaluation_handler("human")
    def handle_human_evaluation(self, prompt: str = "Is the task successful?") -> None:
        """Human evaluation handler."""
        if config.headless:
            feedback = input(
                f"{prompt}\n\nGive your feedback and Press Enter"
                " (Leave blank if successful): "
            )
        else:
            task_status.set_task_state(
                StateInfo(
                    state=StateEnum.WAIT_FOR_INPUT,
                    message=f"{prompt}\n\nGive your feedback and Press Enter (Leave blank if successful): ",  # noqa: E501
                )
            )
            state = task_status.wait_for_state_change(StateEnum.WAIT_FOR_INPUT)
            assert state.state == StateEnum.IN_PROGRESS, state
            assert isinstance(state.message, str), state
            feedback = state.message
        if feedback != "":
            raise FeedbackException(feedback)
