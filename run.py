import argparse
import asyncio
import functools
import logging
import sys

import qasync
from qasync import QApplication

from playground.config import Config
from playground.llm import setup_model
from playground.utils.json_utils import read_jsonl

config = Config()
logger = logging.getLogger(__name__)


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env", type=str, choices=["desktop", "android"], default="desktop"
    )
    parser.add_argument("--agent", type=str, default=config.agent)
    parser.add_argument("--provider", type=str, default=config.provider)
    parser.add_argument("--mode", type=str, choices=["record", "eval"], default="eval")
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)

    return parser


def setup_agent(args):
    model = setup_model(args.provider)
    match args.agent:
        case "dummy":
            from playground.agent.base_agent import Agent

            agent = Agent(
                env=args.env,
                model=model,
                record_path="playground_data/trajectories/dummy",
            )
        case "direct":
            from playground.agent.direct_agent import DirectAgent

            agent = DirectAgent(
                env=args.env,
                model=model,
                record_path="playground_data/trajectories/direct",
            )
        case _:
            raise ValueError(f"Invalid agent: {args.agent}.")

    return agent


def setup_task_and_evaluator(args):
    assert args.env in config.task_config_paths, f"Invalid env {args.env}."
    task_configs = read_jsonl(
        config.task_config_paths[args.env], args.start_idx, args.end_idx
    )

    match args.env:
        case "desktop":
            from playground.env.desktop_env.eval.evaluator_helper import (
                evaluator_router,
            )
        case _:
            raise ValueError(f"Invalid env: {args.env}.")

    return task_configs, evaluator_router


def close_future(future, loop):
    loop.call_later(10, future.cancel)
    future.cancel()


async def eval(args) -> None:
    """Evaluate the agent on the given tasks."""
    loop = asyncio.get_event_loop()
    future: asyncio.Future = asyncio.Future()

    app = QApplication(sys.argv)
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    match args.env:
        case "desktop":
            from playground.env.desktop_env.agent_interface import AgentInterface

            interface = AgentInterface(
                record_path="playground_data/trajectories/human",
            )
        case _:
            raise ValueError(f"Invalid env: {args.env}.")

    # agent = setup_agent(args)
    # task_configs, evaluator_router = setup_task_and_evaluator(args)

    # scores = {}
    # for task_config in task_configs:
    #     try:
    #         task_id = task_config["task_id"]
    #         record_screen = task_config.get("visual", False)
    #         comb = evaluator_router(task_config)
    #         comb.reset()

    #         instruction = task_config["instruction"]
    #         logger.info(f"Task instruction: {instruction}")

    #         agent.reset(
    #             task_id=task_id,
    #             instruction=instruction,
    #             record_screen=record_screen,
    #         )
    #         trajectory = agent.run()

    #         score, feedback = comb(trajectory=trajectory)
    #         scores[task_id] = score
    #         if score == 1.0:
    #             logger.info(f"[Result] (PASS): {feedback}")
    #         else:
    #             logger.info(f"[Result] (FAIL): {feedback}")

    #     except Exception as e:
    #         import traceback

    #         logger.error(f"[Unhandled Error] {repr(e)}]")
    #         logger.error(traceback.format_exc())

    # agent.close()
    # logger.info(f"Average score: {sum(scores.values()) / max(len(scores), 1)}")

    interface.show()

    await future


async def record(args) -> None:
    loop = asyncio.get_event_loop()
    future: asyncio.Future = asyncio.Future()

    app = QApplication(sys.argv)
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(
            functools.partial(close_future, future, loop)
        )

    match args.env:
        case "desktop":
            from playground.env.desktop_env.human_interface import HumanInterface

            interface = HumanInterface(
                record_path="playground_data/trajectories/human",
            )
        case _:
            raise ValueError(f"Invalid env: {args.env}.")

    interface.show()

    await future


def main():
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")

    match args.mode:
        case "eval":
            try:
                qasync.run(eval(args))
            except asyncio.exceptions.CancelledError:
                sys.exit(0)
        case "record":
            try:
                qasync.run(record(args))
            except asyncio.exceptions.CancelledError:
                sys.exit(0)
        case _:
            raise ValueError(f"Invalid mode {args.mode}")


if __name__ == "__main__":
    main()
