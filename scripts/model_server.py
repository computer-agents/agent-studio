import argparse
import logging

import fastapi
import uvicorn
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from agent_studio.config.config import Config
from agent_studio.utils.communication import bytes2str, str2bytes


class ChatCompletionRequest(BaseModel):
    model: str
    messages: str


TIMEOUT_KEEP_ALIVE = 5  # seconds

app = fastapi.FastAPI()

config = Config()
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Gemini API server.")
    parser.add_argument("--host", type=str, default=None, help="host name")
    parser.add_argument("--port", type=int, default=8000, help="port number")
    parser.add_argument(
        "--root-path",
        type=str,
        default=None,
        help="FastAPI root_path when app is behind a path based routing proxy",
    )

    return parser.parse_args()


@app.get("/health")
async def health() -> Response:
    """Health check."""
    return Response(status_code=200, content="OK")


@app.post("/generate")
async def create_chat_completion(request: ChatCompletionRequest) -> JSONResponse:
    messages = str2bytes(request.messages)
    model = request.model
    if "gemini" in model:
        from agent_studio.llm.gemini import GeminiProvider

        message, info = GeminiProvider().generate_response(messages, model=model)
    elif "gpt" in model:
        from agent_studio.llm.openai import OpenAIProvider

        message, info = OpenAIProvider().generate_response(messages, model=model)
    else:
        raise NotImplementedError
    return JSONResponse(
        content={
            "message": bytes2str(message),
            "info": bytes2str(info),
        }
    )


if __name__ == "__main__":
    args = parse_args()

    app.root_path = args.root_path
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        timeout_keep_alive=TIMEOUT_KEEP_ALIVE,
    )
