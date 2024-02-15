import argparse
import logging
import uuid

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
    parser.add_argument("--agent", type=str, default="dummy")
    parser.add_argument("--model", type=str, default="default")
    parser.add_argument("--mode", type=str, choices=["record", "eval"], default="eval")
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)

    return parser


def setup_agent(args):
    model = setup_model(args.model)
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


def eval(args) -> None:
    """Evaluate the agent on the given tasks."""

    agent = setup_agent(args)
    task_configs, evaluator_router = setup_task_and_evaluator(args)

    scores = {}
    for task_config in task_configs:
        try:
            task_id = task_config["task_id"]
            record_screen = task_config.get("visual", False)
            comb = evaluator_router(task_config)
            comb.reset()

            instruction = task_config["instruction"]
            logger.info(f"Task instruction: {instruction}")

            agent.reset(
                task_id=task_id,
                instruction=instruction,
                record_screen=record_screen,
            )
            trajectory = agent.run()

            score = comb(trajectory=trajectory)
            scores[task_id] = score
            if score == 1.0:
                logger.info("[Result] (PASS)")
            else:
                logger.info("[Result] (FAIL)")

        except Exception as e:
            import traceback

            logger.error(f"[Unhandled Error] {repr(e)}]")
            logger.error(traceback.format_exc())

    agent.close()
    logger.info(f"Average score: {sum(scores.values()) / len(scores)}")


def record(args) -> None:
    match args.env:
        case "desktop":
            from playground.env.desktop_env.recorder.human_recorder import HumanRecorder

            recorder = HumanRecorder(
                record_path="playground_data/trajectories/human",
                video_fps=config.video_fps,
                mouse_fps=config.mouse_fps,
            )
        case _:
            raise ValueError(f"Invalid env: {args.env}.")

    while True:
        instruction = input("Enter task instruction (or type 'q' to exit): ")
        if instruction == "q":
            break
        else:
            record_screen = input("Is this task visual? (y/n): ").lower() == "y"
            input(
                "Press Enter to start recording. During recording, "
                f"you can press {config.stop_hotkeys} to stop."
            )
            task_id = str(uuid.uuid4())
            recorder.reset(
                task_id=task_id, instruction=instruction, record_screen=record_screen
            )
            recorder.start()
            recorder.wait_exit()


def main():
    parser = create_parser()
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")

    match args.mode:
        case "eval":
            eval(args)
        case "record":
            record(args)
        case _:
            raise ValueError(f"Invalid mode {args.mode}")


if __name__ == "__main__":
    main()
