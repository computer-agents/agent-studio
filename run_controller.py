import argparse
import logging
import time

import requests

from playground.config import Config
from playground.utils.json_utils import read_jsonl
from playground.llm import setup_model
from playground.utils.communication import bytes2str, \
    PlaygroundResponse, PlaygroundResetRequest, \
    PlaygroundStatusResponse, PlaygroundResultResponse

from rich import traceback
traceback.install(show_locals=True)

config = Config()
logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env", type=str, choices=["desktop", "android"], default="desktop"
    )
    parser.add_argument("--agent", type=str, default=config.agent)
    parser.add_argument("--provider", type=str, default=config.provider)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)

    return parser


def setup_agent(
    provider: str,
    env: str,
    agent_name: str,
):
    model = setup_model(provider)
    match agent_name:
        case "dummy":
            from playground.agent.base_agent import Agent

            agent = Agent(
                env=env,
                model=model,
                record_path="playground_data/trajectories/dummy",
            )
        case "direct":
            from playground.agent.direct_agent import DirectAgent

            agent = DirectAgent(
                env=env,
                model=model,
                record_path="playground_data/trajectories/direct",
            )
        case _:
            raise ValueError(f"Invalid agent: {agent_name}.")

    return agent


def setup_task(args):
    assert args.env in config.task_config_paths, f"Invalid env {args.env}."
    task_configs = read_jsonl(
        config.task_config_paths[args.env], args.start_idx, args.end_idx
    )
    return task_configs


def wait_finish():
    while True:
        response_raw = requests.get(f"http://{config.env_server_addr}:{config.env_server_port}/task/status")
        response = PlaygroundStatusResponse(**response_raw.json())
        if response.status == "finished":
            break
        elif response.status == "wait_for_input":
            confirmation = input(f"{response.content}\n")
            requests.post(f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm", json={"message":confirmation})
        else:
            assert response.status in ["pending", "in_progress"]
        time.sleep(1)

def main():
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")
    task_configs = setup_task(args)
    agent = setup_agent(
        provider=args.provider,
        env=args.env,
        agent_name=args.agent,
    )
    task_config = task_configs[0]
    task_id = task_config["task_id"]
    instruction = task_config["instruction"]
    record_screen = task_config.get("visual", False)
    response_raw = requests.post(f"http://{config.env_server_addr}:{config.env_server_port}/task/reset", json=PlaygroundResetRequest(task_config=task_config).model_dump())
    response = PlaygroundResponse(**response_raw.json())
    print(response)
    wait_finish()
    response_raw = requests.get(f"http://{config.env_server_addr}:{config.env_server_port}/task/result")
    response = PlaygroundResultResponse(**response_raw.json())
    assert response.result == "success" and response.status == "finished"

    agent.reset(
        task_id=task_id,
        instruction=instruction,
        record_screen=record_screen,
    )
    trajectory = agent.run()
    print(trajectory)
    response_raw = requests.post(f"http://{config.env_server_addr}:{config.env_server_port}/task/eval", json={"task_config":task_config, "trajectory": bytes2str(trajectory)})
    response = PlaygroundResponse(**response_raw.json())
    print(response)
    wait_finish()
    response_raw = requests.get(f"http://{config.env_server_addr}:{config.env_server_port}/task/result")
    response = PlaygroundResultResponse(**response_raw.json())
    assert response.status == "finished" and isinstance(response.message, dict)
    print(response.result, response.message["score"], response.message["feedback"])
    print("Done!")

class TestReq():
    text: str
    def __init__(self, text: str):
        self.text = text


if __name__ == "__main__":
    main()
