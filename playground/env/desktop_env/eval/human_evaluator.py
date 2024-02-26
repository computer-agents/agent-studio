import logging

from playground.env.desktop_env.eval.evaluator import Evaluator
from playground.utils.task_status import TaskStatus, StateEnum, StateInfo

logger = logging.getLogger(__name__)
task_status = TaskStatus()


class HumanEvaluator(Evaluator):
    name: str = "human"

    def __call__(self, **kwargs) -> tuple[float, str]:
        task_status.set_task_state(StateInfo(
            state=StateEnum.WAIT_FOR_INPUT,
            message="Is the task successful? (y/n): ")
        )
        state = task_status.wait_not_state(StateEnum.WAIT_FOR_INPUT)
        score = float(state.message == "y")
        task_status.set_task_state(StateInfo(
            state=StateEnum.WAIT_FOR_INPUT,
            message="Type any feedback and press Enter (or press Enter to skip): ")
        )
        state = task_status.wait_not_state(StateEnum.WAIT_FOR_INPUT)
        feedback = state.message
        # score = float(input("Is the task successful? (y/n): ") == "y")
        # feedback = input("Type any feedback and press Enter (or press Enter to skip): ")
        return score, feedback
