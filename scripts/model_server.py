import argparse
import base64
import json
import logging
import pickle

import fastapi
import google.generativeai as genai
import PIL.PngImagePlugin
import uvicorn
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from playground.config.config import Config

PIL.PngImagePlugin


class ChatCompletionRequest(BaseModel):
    model: str
    messages: str
    config: str


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
    return Response(status_code=200)


@app.post("/generate")
async def create_chat_completion(request: ChatCompletionRequest) -> JSONResponse:
    if request.model in ["gemini-pro-vision", "gemini-pro"]:
        with open(config.api_key_path, "r") as f:
            api_keys = json.load(f)
        genai.configure(api_key=api_keys["gemini"])
        model = genai.GenerativeModel(request.model)
    else:
        raise NotImplementedError

    messages = pickle.loads(base64.b64decode(request.messages.encode("utf-8")))
    generation_config = pickle.loads(base64.b64decode(request.config.encode("utf-8")))
    logger.info(
        f"Generating content with messages: {messages}"
        f" and generation_config: {generation_config}"
    )
    r = model.generate_content(messages, generation_config=generation_config)
    token_count = model.count_tokens(messages)
    try:
        print(r.text)
    except ValueError:
        # TODO: Remove this after debugging
        for candidate in r.candidates:
            print("Finish Reason: ", candidate.finish_reason)
            message = [part.text for part in candidate.content.parts]
            print("Message: ", message)
    return JSONResponse(
        content={
            "content": base64.b64encode(pickle.dumps(r)).decode("utf-8"),
            "token_count": token_count.total_tokens,
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
