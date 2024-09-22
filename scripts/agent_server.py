import logging
import threading
from contextlib import asynccontextmanager
from typing import Any

import jsonpickle
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response

from agent_studio.agent.runtime import PythonRuntime
from agent_studio.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator_helper import (
    EvaluatorComb,
    evaluator_router,
)
from agent_studio.utils.communication import (
    AgentStudioEvalRequest,
    AgentStudioResetRequest,
    AgentStudioStatusResponse,
    AgentStudioTextRequest,
)
from agent_studio.utils.task_status import StateEnum, StateInfo, TaskStatus
from agent_studio.utils.types import Procedure, TaskConfig

config = Config()
logger = logging.getLogger(__name__)
task_status = TaskStatus()

runtimes: dict[str, PythonRuntime] = {}
config.remote = False
config.headless = False
config.need_human_confirmation = True

current_thread: None | threading.Thread = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtimes["python"] = PythonRuntime()
    yield
    runtimes["python"].close()


app = FastAPI(lifespan=lifespan)


def reset_thread(comb: EvaluatorComb, procedures: list[Procedure]):
    try:
        comb.reset(procedures)
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message="", result="success")
        )
        logger.info("Finished resetting task")
    except Exception as e:
        logger.error(f"Failed to reset task: {e}")
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message=str(e), result="error")
        )


def eval_task(comb: EvaluatorComb, procedures: list[Procedure], **kwargs: Any):
    try:
        score, feedback = comb(procedures, **kwargs)
        task_status.set_task_state(
            StateInfo(
                state=StateEnum.FINISHED,
                message={"score": score, "feedback": feedback},
                result="success",
            )
        )
        logger.info("Finished evaluating task")
    except Exception as e:
        logger.error(f"Failed to evaluate task: {e}")
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message=str(e), result="error")
        )


@app.get("/health")
async def health() -> Response:
    """Health check."""
    return Response(status_code=200, content="OK")


@app.post("/execute")
async def execute_code(request: AgentStudioTextRequest) -> dict:
    logger.info(f"Execute code: {request.message}")
    result = runtimes["python"](request.message)
    return result


@app.post("/runtime/reset")
async def reset_runtime() -> AgentStudioStatusResponse:
    runtimes["python"].close()
    runtimes["python"] = PythonRuntime()
    logger.info("Reset runtime")
    return AgentStudioStatusResponse(status="success")


@app.get("/env_vars")
async def get_env_vars() -> AgentStudioStatusResponse:
    env_vars = config.env_vars
    return AgentStudioStatusResponse(status="success", message=env_vars)

def wait_for_state_shift(last_state: StateEnum) -> AgentStudioStatusResponse:
    cur_status = task_status.wait_for_state_change(last_state)
    if cur_status.state == StateEnum.WAIT_FOR_INPUT:
        assert isinstance(
            cur_status.message, str
        ), f"Invalid message: {cur_status.message}"
        return AgentStudioStatusResponse(
            status=cur_status.state.value,
            content=cur_status.message,
        )
    elif cur_status.state == StateEnum.FINISHED:
        global current_thread
        if current_thread is None:
            raise ValueError("Invalid current_thread")
        current_thread.join()
        current_thread = None
        return AgentStudioStatusResponse(
            status=cur_status.state.value,
            content=cur_status.result,
            message=cur_status.message,
        )
    else:
        raise ValueError(f"Invalid state: {cur_status}")


@app.post("/task/confirm")
async def confirm(request: AgentStudioTextRequest) -> AgentStudioStatusResponse:
    """
    Confirm critical action.

    Args:
        request:
            message: User input.

    Returns:
        The status of the task.
    """
    global current_thread
    assert current_thread is not None, "Invalid current_thread"
    cur_state = task_status.get_task_state().state
    assert cur_state == StateEnum.WAIT_FOR_INPUT, f"Invalid status: {cur_state}"
    task_status.set_task_state(
        StateInfo(state=StateEnum.IN_PROGRESS, message=request.message)
    )
    try:
        return wait_for_state_shift(StateEnum.IN_PROGRESS)
    except Exception as e:
        return AgentStudioStatusResponse(status="error", content=str(e))


@app.post("/task/reset")
async def reset_task(request: AgentStudioResetRequest) -> AgentStudioStatusResponse:
    """
    Reset the task.

    Returns:
        The status of the task.
    """
    global current_thread
    cur_status = task_status.get_task_state()
    if cur_status.state != StateEnum.FINISHED:
        logger.info(
            f"Stopping current task: {cur_status.state}, on thread: {current_thread}"
        )
        assert current_thread is not None, "Invalid current_thread"
        task_status.set_task_state(StateInfo(StateEnum.TERMINATE))
        current_thread.join()
        task_status.reset_state()

    logger.info(f"Reset task with procedures: {request.procedures}")
    try:
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        fake_task_config = TaskConfig(
            task_id="fake",
            instruction="fake",
            visual=False,
            max_steps=100,
            max_time=100,
            eval_procedure=[],
            reset_procedure=request.procedures,
            cleanup_procedure=[],
        )
        comb = evaluator_router(fake_task_config)
        current_thread = threading.Thread(
            target=reset_thread,
            args=(
                comb,
                fake_task_config.reset_procedure,
            ),
        )
        current_thread.start()
        return wait_for_state_shift(StateEnum.IN_PROGRESS)
    except Exception as e:
        return AgentStudioStatusResponse(status="error", content=str(e))


@app.post("/task/eval")
async def submit_eval(request: AgentStudioEvalRequest) -> AgentStudioStatusResponse:
    """
    Evaluate the given task.

    Args:
        request:
            task_config: The task configuration.
            trajectory: The trajectory of the agent.

    Returns:
        The evaluation result.
            If successful, the result contains the score and feedback.
            If failed, the result contains the error message.

    Returns:
        The status of the task.
    """

    try:
        global current_thread
        if current_thread is not None:
            raise ValueError("Another task is in progress.")
        logger.info(f"Start evaluating task: {request.procedures}")
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        kwargs = jsonpickle.decode(request.kwargs)
        if not isinstance(kwargs, dict):
            raise ValueError(f"kwargs is {type(kwargs)} instead of a dict")

        fake_task_config = TaskConfig(
            task_id="fake",
            instruction="fake",
            visual=False,
            max_steps=100,
            max_time=100,
            eval_procedure=request.procedures,
            reset_procedure=[],
            cleanup_procedure=[],
        )
        comb = evaluator_router(fake_task_config)
        current_thread = threading.Thread(
            target=eval_task,
            args=(
                comb,
                fake_task_config.eval_procedure,
            ),
            kwargs=kwargs,
        )
        current_thread.start()
        return wait_for_state_shift(StateEnum.IN_PROGRESS)
    except Exception as e:
        return AgentStudioStatusResponse(status="error", content=str(e))


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.env_server_host,
        port=config.env_server_port,
    )
