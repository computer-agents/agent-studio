import argparse
from contextlib import asynccontextmanager
import logging
import base64
import pickle
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from playground.config import Config
from playground.utils.task_status import TaskStatus, StateEnum, StateInfo
from playground.agent.runtime import PythonRuntime

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
    runtimes["python"].exec(init_code)
    yield
    runtimes["python"].close()


app = FastAPI(lifespan=lifespan)


class PlaygroundRequest(BaseModel):
    message: str


class PlaygroundEvalRequest(BaseModel):
    task_config: dict
    trajectory: str


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env", type=str, choices=["desktop", "android"], default="desktop"
    )

    return parser


def setup_evaluator(
        env: str,
):
    assert env in config.task_config_paths, f"Invalid env {env}."

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
        task_status.set_task_state(StateInfo(StateEnum.FINISHED, {"status": "success"}))
    except Exception as e:
        logger.error(f"Failed to reset task: {e}")
        task_status.set_task_state(StateInfo(StateEnum.FINISHED, {"status": "error", "message": str(e)}))


def eval_task(task_config: dict, trajectory: list):
    try:
        task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS))
        evaluator_router = setup_evaluator(
            env=args.env,
        )
        comb = evaluator_router(task_config)
        score, feedback = comb(trajectory=trajectory)
        task_status.set_task_state(StateInfo(
            StateEnum.FINISHED,
            {"status": "success", "score": score, "feedback": feedback}
        ))
    except Exception as e:
        logger.error(f"Failed to evaluate task: {e}")
        task_status.set_task_state(StateInfo(
            StateEnum.FINISHED, {"status": "error", "message": str(e)}
        ))


@app.get("/health")
async def health() -> Response:
    """Health check."""
    return Response(status_code=200, content="OK")


@app.post("/execute")
async def execute_code(request: PlaygroundRequest) -> JSONResponse:
    result = runtimes["python"].exec(request.message)
    return JSONResponse(content=result)


@app.post("/task/confirm")
async def confirm(request: PlaygroundRequest) -> JSONResponse:
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
    task_status.set_task_state(StateInfo(StateEnum.IN_PROGRESS, request.message))
    return JSONResponse(content={"status": "success"})


@app.post("/task/reset")
async def new_task(request: PlaygroundRequest) -> JSONResponse:
    """
    Reset the task.

    Args:
        request:
            message: dict : The task configuration.
    """
    cur_status = task_status.get_task_state()
    assert cur_status.state == StateEnum.PENDING, \
        f"Invalid status: {cur_status}"
    task_config = eval(request.message)
    threading.Thread(target=reset_task, args=(task_config,)).start()
    return JSONResponse(
        content={
            "status": "submitted",
        }
    )


@app.post("/task/eval")
async def submit_eval(request: PlaygroundEvalRequest) -> JSONResponse:
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
    assert cur_status.state == StateEnum.PENDING, \
        f"Invalid status: {cur_status}"
    threading.Thread(
        target=eval_task,
        args=(
            request.task_config,
            pickle.loads(base64.b64decode(request.trajectory.encode("utf-8")))
        )
    ).start()
    return JSONResponse(
        content={
            "status": "submitted",
        }
    )


@app.get("/task/status")
async def get_status() -> JSONResponse:
    """
    Get the status of the current task.
    """
    cur_status = task_status.get_task_state()
    if cur_status.state == StateEnum.PENDING:
        return JSONResponse(content={"status": "pending"})
    elif cur_status.state == StateEnum.IN_PROGRESS:
        return JSONResponse(content={"status": "in_progress"})
    elif cur_status.state == StateEnum.WAIT_FOR_INPUT:
        return JSONResponse(content={"status": "wait_for_input", "message": cur_status.info})
    elif cur_status.state == StateEnum.FINISHED:
        return JSONResponse(content={"status": "finished"})
    else:
        raise ValueError(f"Invalid state: {cur_status}")


@app.get("/task/result")
async def get_result() -> JSONResponse:
    """
    Get the result of the current task.
    """
    cur_status = task_status.get_task_state()
    assert cur_status.state == StateEnum.FINISHED, f"Invalid status: {cur_status}"
    encoded_result = base64.b64encode(pickle.dumps(obj=cur_status.info)).decode("utf-8")
    task_status.reset_state()
    return JSONResponse(content={"result": encoded_result})


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")
    uvicorn.run(
        app,
        host=config.env_server_host,
        port=config.env_server_port,
    )

