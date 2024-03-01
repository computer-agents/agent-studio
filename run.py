import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any

import qasync
from qasync import QApplication
import psutil
import requests
from PIL import Image

from playground.config import Config
from playground.env.desktop_env.eval.evaluator_helper import evaluator_router
from playground.env.desktop_env.agent_interface import AgentInterface
from playground.llm import setup_model
from playground.utils.json_utils import read_jsonl, add_jsonl
from playground.env.desktop_env.recorder.screen_recorder import ScreenRecorder

config = Config()
logger = logging.getLogger(__name__)
class TestReq():
    text: str
    def __init__(self, text: str):
        self.text = text

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

            agent = Agent(model=model)
            record_path = "playground_data/trajectories/dummy"
        case "direct":
            from playground.agent.direct_agent import DirectAgent

            agent = DirectAgent(model=model)
            record_path = "playground_data/trajectories/direct"
        case _:
            raise ValueError(f"Invalid agent: {args.agent}.")

    return agent, record_path


def setup_tasks(args):
    assert args.env in config.task_config_paths, f"Invalid env {args.env}."
    task_configs = read_jsonl(
        config.task_config_paths[args.env], args.start_idx, args.end_idx
    )

    return task_configs


def eval(args) -> None:
    """Evaluate the agent on the given tasks."""

    agent, record_path = setup_agent(args)
    # agent = setup_agent(config.provider, config.env_type, config.agent)
    task_configs = setup_tasks(args)

    match args.env:
        case "desktop":
            if not config.headless:
                from playground.env.desktop_env.agent_interface import run_ui

                try:
                    if not config.remote:
                        import atexit
                        local_agent_server = psutil.Popen(
                            [
                                "python",
                                "scripts/agent_server.py",
                                "--env",
                                "desktop",
                            ]
                        )
                        def cleanup(local_agent_server: psutil.Process):
                            local_agent_server.terminate()
                            local_agent_server.wait()

                        atexit.register(cleanup, local_agent_server)

                    while True:
                        try:
                            response = requests.get(
                                f"http://{config.env_server_addr}:{config.env_server_port}/health"
                            )
                            if response.status_code == 200:
                                break
                        except Exception:
                            logger.info("Waiting for the agent server to start...")
                            time.sleep(1)

                    if not config.remote:
                        app = QApplication(sys.argv)
                        interface = AgentInterface(
                            agent=agent,
                            task_configs=task_configs,
                            record_path=record_path,
                        )
                        interface.show()
                        sys.exit(app.exec())
                    else:
                        qasync.run(
                            run_ui(
                                agent=agent,
                                task_configs=task_configs,
                                record_path=record_path,
                            )
                        )
                    # TODO: can we use qasync.run when remote = False?
                except asyncio.exceptions.CancelledError:
                    sys.exit(0)

            else:
                assert not config.remote, "Headless mode does not support remote agent."
                import pyautogui
                video_width, video_height = pyautogui.size()
                scores = {}
                for task_config in task_configs:
                    try:
                        task_id = task_config["task_id"]
                        if task_config['visual']:
                            recorder = ScreenRecorder(
                                fps=config.video_fps,
                                screen_region={
                                    "top": 0,
                                    "left": 0,
                                    "width": video_width,
                                    "height": video_height,
                                },
                            )
                            recorder.start()
                        comb = evaluator_router(task_config)
                        comb.reset()

                        instruction = task_config["instruction"]
                        logger.info(f"Task instruction: {instruction}")

                        agent.reset(instruction=instruction)
                        # Loop until the task is done or the max step is reached.
                        for t in range(config.max_step):
                            logger.info(f"Step {t}")
                            if task_config['visual']:
                                obs = recorder.get_current_frame()
                            else:
                                obs = None
                            _, done = agent.step(obs=obs)
                            if done:
                                break

                        # TODO: add agent self-eval

                        logger.info("Start auto-evaluation")
                        score, feedback = comb(trajectory=agent.trajectory)
                        scores[task_id] = score
                        if score == 1.0:
                            logger.info(f"[Result] (PASS): {feedback}")
                        else:
                            logger.info(f"[Result] (FAIL): {feedback}")

                        task_trajectory_path = Path(record_path) / f"{task_id}"
                        record_dict: dict[str, Any] = {
                            "task_config": task_config,
                        }
                        if task_config['visual']:
                            assert recorder is not None
                            recorder.stop()
                            recorder.wait_exit()
                            video_path = (task_trajectory_path / "video.mp4").as_posix()
                            recorder.save(video_path, start_frame_id=0)
                            logger.info(f"Video saved to {video_path}")

                            record_dict["video"] = {
                                "path": video_path,
                            }
                            del recorder
                            recorder = None
                        else:
                            record_dict["video"] = None

                        trajectory = agent.get_trajectory()
                        record_dict["actions"] = []
                        for idx, action in enumerate(trajectory):
                            im = Image.fromarray(action["obs"])
                            img_path = (task_trajectory_path / (f"{idx}.png")).as_posix()
                            im.save(img_path)
                            record_dict["actions"].append(
                                {
                                    "timestamp": action["timestamp"],
                                    "obs": img_path,
                                    "action": action["act"],
                                    "result": action["res"],
                                }
                            )

                        record_dict["score"] = str(score)
                        record_dict["feedback"] = feedback
                        add_jsonl(
                            data=[record_dict],
                            file_path=(Path(record_path) / "tasks.jsonl").as_posix(),
                        )
                    except KeyboardInterrupt:
                        if recorder is not None:
                            recorder.stop()
                            recorder.wait_exit()
                        agent.close()
                    except Exception as e:
                        import traceback

                        logger.error(f"[Unhandled Error] {repr(e)}]")
                        logger.error(traceback.format_exc())

                agent.close()
                logger.info(
                    f"Average score: {sum(scores.values()) / max(len(scores), 1)}"
                )

        case _:
            raise ValueError(f"Invalid env: {args.env}.")


def record(args) -> None:
    match args.env:
        case "desktop":
            from playground.env.desktop_env.human_interface import run_ui

            try:
                qasync.run(run_ui(record_path="playground_data/trajectories/human"))
            except asyncio.exceptions.CancelledError:
                sys.exit(0)
        case _:
            raise ValueError(f"Invalid env: {args.env}.")


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
