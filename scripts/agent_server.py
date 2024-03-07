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

config = Config()
logger = logging.getLogger(__name__)
task_status = TaskStatus()

runtimes: dict[str, PythonRuntime] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    runtimes["python"] = PythonRuntime()
    init_code = (
        "from playground.env.desktop_env import Shell, Keyboard, Mouse\n\n"
        "shell = Shell()\nkeyboard = Keyboard()\nmouse = Mouse()\n"
    )
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


def reset_task(task_config: dict):
    try:
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        evaluator_router = setup_evaluator(
            env=args.env,
        )
        comb = evaluator_router(task_config)
        comb.reset()
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message="", result="success")
        )
    except Exception as e:
        logger.error(f"Failed to reset task: {e}")
        task_status.set_task_state(
            StateInfo(state=StateEnum.FINISHED, message=str(e), result="error")
        )


def eval_task(task_config: dict):
    try:
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        evaluator_router = setup_evaluator(
            env=args.env,
        )
        comb = evaluator_router(task_config)
        score, feedback = comb()
        task_status.set_task_state(
            StateInfo(
                state=StateEnum.FINISHED,
                message={"score": score, "feedback": feedback},
                result="success",
            )
        )
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
    result = runtimes["python"](request.message)
    return result


@app.post("/runtime/reset")
async def reset_runtime() -> PlaygroundResponse:
    runtimes["python"].close()
    runtimes["python"] = PythonRuntime()
    init_code = (
        "from playground.env.desktop_env import Shell, Keyboard, Mouse\n\n"
        "shell = Shell()\nkeyboard = Keyboard()\nmouse = Mouse()\n"
    )
    runtimes["python"](init_code)
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
    cur_status = task_status.get_task_state()
    assert cur_status.state in [
        StateEnum.PENDING,
        StateEnum.FINISHED,
    ], f"Invalid status: {cur_status}"
    threading.Thread(target=reset_task, args=(request.task_config,)).start()
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
    cur_status = task_status.get_task_state()
    assert cur_status.state in [
        StateEnum.PENDING,
        StateEnum.FINISHED,
    ], f"Invalid status: {cur_status}"
    threading.Thread(
        target=eval_task,
        args=(request.task_config,),
    ).start()
    return PlaygroundResponse(status="submitted")


@app.get("/task/status")
async def get_status() -> PlaygroundStatusResponse:
    """
    Get the status of the current task.
    """
    cur_status = task_status.get_task_state()
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
    else:
        raise ValueError(f"Invalid state: {cur_status}")


@app.get("/task/result")
async def get_result() -> PlaygroundResultResponse:
    """
    Get the result of the current task.
    """
    cur_status = task_status.get_task_state()
    assert cur_status.state == StateEnum.FINISHED, f"Invalid status: {cur_status}"
    task_status.reset_state()
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
