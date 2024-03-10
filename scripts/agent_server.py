import argparse
import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response

from playground.agent.runtime import PythonRuntime
from playground.config import Config
from playground.utils.communication import (
    PlaygroundEvalRequest,
    PlaygroundResetRequest,
    PlaygroundResponse,
    PlaygroundResultResponse,
    PlaygroundStatusResponse,
    PlaygroundTextRequest,
)
from playground.utils.task_status import StateEnum, StateInfo, TaskStatus
from playground.env.desktop_env.eval.evaluator_helper import EvaluatorComb

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
    with open(config.init_code_path, "r") as f:
        init_code = f.read()
    runtimes["python"](init_code)
    yield
    runtimes["python"].close()


app = FastAPI(lifespan=lifespan)


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env", type=str, choices=["desktop", "android"], default="desktop"
    )

    return parser


def setup_evaluator(
    env: str,
):
    match env:
        case "desktop":
            from playground.env.desktop_env.eval.evaluator_helper import (
                evaluator_router,
            )
        case _:
            raise ValueError(f"Invalid env: {env}.")

    return evaluator_router


def reset_task(comb: EvaluatorComb):
    try:
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        comb.reset()
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message="", result="success")
        )
        logger.info("Finished resetting task")
    except Exception as e:
        logger.error(f"Failed to reset task: {e}")
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message=str(e), result="error")
        )


def eval_task(comb: EvaluatorComb):
    try:
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        score, feedback = comb()
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
async def execute_code(request: PlaygroundTextRequest) -> dict:
    logger.info(f"Execute code: {request.message}")
    result = runtimes["python"](request.message)
    return result


@app.post("/runtime/reset")
async def reset_runtime() -> PlaygroundResponse:
    runtimes["python"].close()
    runtimes["python"] = PythonRuntime()
    with open(config.init_code_path, "r") as f:
        init_code = f.read()
    runtimes["python"](init_code)
    logger.info("Reset runtime")
    return PlaygroundResponse(status="success")


@app.post("/task/confirm")
async def confirm(request: PlaygroundTextRequest) -> PlaygroundResponse:
    """
    Confirm critical action.

    Args:
        request:
            message: User input.

    Returns:
        Always "success".
    """
    global current_thread
    assert current_thread is not None, "Invalid current_thread"
    cur_state = task_status.get_task_state().state
    assert cur_state == StateEnum.WAIT_FOR_INPUT, f"Invalid status: {cur_state}"
    task_status.set_task_state(
        StateInfo(state=StateEnum.IN_PROGRESS, message=request.message)
    )
    return PlaygroundResponse(status="success")


@app.post("/task/reset")
async def new_task(request: PlaygroundResetRequest) -> PlaygroundResponse:
    """
    Reset the task.

    Args:
        request:
            task_config: The task configuration.
    """
    global current_thread
    cur_status = task_status.get_task_state()
    if cur_status.state not in [StateEnum.PENDING, StateEnum.FINISHED]:
        logger.info(
            f"Stopping current task: {cur_status.state}, on thread: {current_thread}"
        )
        assert current_thread is not None, "Invalid current_thread"
        task_status.set_task_state(StateInfo(StateEnum.TERMINATE))
        current_thread.join()
        task_status.reset_state()

    logger.info(f"Start resetting task: {request.task_config}")
    evaluator_router = setup_evaluator(
        env=args.env,
    )
    comb = evaluator_router(request.task_config)
    current_thread = threading.Thread(target=reset_task, args=(comb,))
    current_thread.start()
    return PlaygroundResponse(status="submitted")


@app.post("/task/eval")
async def submit_eval(request: PlaygroundEvalRequest) -> PlaygroundResponse:
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
    """
    global current_thread
    assert current_thread is not None, "Invalid current_thread"
    cur_status = task_status.get_task_state()
    assert cur_status.state in [
        StateEnum.PENDING,
        StateEnum.FINISHED,
    ], f"Invalid status: {cur_status}"

    evaluator_router = setup_evaluator(
        env=args.env,
    )
    logger.info(f"Start evaluating task: {request.task_config}")
    comb: EvaluatorComb = evaluator_router(request.task_config)
    current_thread = threading.Thread(
        target=eval_task,
        args=(comb,),
    )
    current_thread.start()
    return PlaygroundResponse(status="submitted")


@app.get("/task/status")
async def get_status() -> PlaygroundStatusResponse:
    """
    Get the status of the current task.
    """
    cur_status = task_status.get_task_state()
    logger.debug(f"Get current status: {cur_status}")
    if cur_status.state == StateEnum.PENDING:
        return PlaygroundStatusResponse(status="pending")
    elif cur_status.state == StateEnum.IN_PROGRESS:
        return PlaygroundStatusResponse(status="in_progress")
    elif cur_status.state == StateEnum.WAIT_FOR_INPUT:
        assert isinstance(
            cur_status.message, str
        ), f"Invalid message: {cur_status.message}"
        return PlaygroundStatusResponse(
            status="wait_for_input", content=cur_status.message
        )
    elif cur_status.state == StateEnum.FINISHED:
        return PlaygroundStatusResponse(status="finished")
    elif cur_status.state == StateEnum.TERMINATE:
        return PlaygroundStatusResponse(status="terminate")
    else:
        raise ValueError(f"Invalid state: {cur_status}")


@app.get("/task/result")
async def get_result() -> PlaygroundResultResponse:
    """
    Get the result of the current task.
    """
    cur_status = task_status.get_task_state()
    assert cur_status.state == StateEnum.FINISHED, f"Invalid status: {cur_status}"
    return PlaygroundResultResponse(
        status=cur_status.state.value,
        result=cur_status.result,
        message=cur_status.message,
    )


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")
    uvicorn.run(
        app,
        host=config.env_server_host,
        port=config.env_server_port,
    )
