from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from playground.agent.runtime import PythonRuntime
from playground.config.config import Config

config = Config()


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


class CodeExecutionRequest(BaseModel):
    code: str


@app.get("/health")
async def health() -> Response:
    """Health check."""
    return Response(status_code=200)


@app.post("/execute")
async def execute_code(request: CodeExecutionRequest) -> JSONResponse:
    result = runtimes["python"].exec(request.code)
    return JSONResponse(content=result)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.host,
        port=config.jupyter_port,
    )
