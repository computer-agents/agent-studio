import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

import psutil
import qasync
import requests
from qasync import QApplication

from playground.config import Config
from playground.env.desktop_env.agent_interface import AgentInterface
from playground.env.desktop_env.eval.evaluator_helper import evaluator_router
from playground.env.desktop_env.recorder.screen_recorder import (
    ScreenRecorder,
    VNCRecorder,
)
from playground.utils.communication import (
    PlaygroundResetRequest,
    PlaygroundResponse,
    PlaygroundResultResponse,
    PlaygroundStatusResponse,
    PlaygroundTextRequest,
    PlaygroundEvalRequest,
)
from playground.agent.base_agent import Agent
from playground.env.desktop_env.vnc_client import VNCStreamer
from playground.llm import setup_model
from playground.utils.human_utils import confirm_action
from playground.utils.json_utils import export_trajectories, read_jsonl

config = Config()
logger = logging.getLogger(__name__)


class TestReq:
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
            record_path = f"playground_data/trajectories/{args.provider}/dummy"
        case "direct":
            from playground.agent.direct_agent import DirectAgent

            agent = DirectAgent(model=model)
            record_path = f"playground_data/trajectories/{args.provider}/direct"
        case _:
            raise ValueError(f"Invalid agent: {args.agent}.")

    Path(record_path).mkdir(parents=True, exist_ok=True)

    return agent, record_path


def setup_tasks(args):
    assert args.env in config.task_config_paths, f"Invalid env {args.env}."
    task_configs = read_jsonl(
        config.task_config_paths[args.env], args.start_idx, args.end_idx
    )

    return task_configs


def wait_finish():
    while True:
        response_raw = requests.get(
            f"http://{config.env_server_addr}:{config.env_server_port}/task/status"
        )
        response = PlaygroundStatusResponse(**response_raw.json())
        if response.status == "finished":
            break
        elif response.status == "wait_for_input":
            if config.need_human_confirmation:
                user_input = input(f"{response.content}")
            else:
                user_input = "y"
            response_raw = requests.post(
                url=f"http://{config.env_server_addr}:{config.env_server_port}/task/confirm",  # noqa: E501
                json=PlaygroundTextRequest(message=user_input).model_dump(),
            )
            response = PlaygroundResponse(**response_raw.json())
            assert response.status == "success"
        elif response.status in ["pending", "in_progress"]:
            pass
        else:
            raise ValueError(f"Unknown status: {response.status}")
        time.sleep(1)


def eval_gui(
    agent: Agent,
    task_configs: list[dict],
    record_path: str,
) -> None:
    """Evaluate the agent on the given tasks with GUI."""
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
                    f"http://{config.env_server_addr}:"
                    f"{config.env_server_port}/health"
                )
                if response.status_code == 200:
                    break
            except Exception:
                logger.info("Waiting for the agent server to start...")
                time.sleep(1)

        app = QApplication(sys.argv)
        interface = AgentInterface(
            agent=agent,
            task_configs=task_configs,
            record_path=record_path,
        )
        interface.showMaximized()
        sys.exit(app.exec())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)



def eval_headless(
    agent: Agent,
    task_configs: list[dict],
    record_path: str,
) -> None:
    """Evaluate the agent on the given tasks in Terminal."""
    scores = {}
    screen_recorder: ScreenRecorder | None = None
    vnc_streamer: VNCStreamer | None = None
    for task_config in task_configs:
        try:
            task_id = task_config["task_id"]
            if config.remote:
                if task_config["visual"]:
                    vnc_streamer = VNCStreamer(
                        env_server_addr=config.env_server_addr,
                        vnc_port=config.vnc_port,
                        vnc_password=config.vnc_password,
                    )
                    vnc_streamer.start()
                    screen_recorder = VNCRecorder(
                        fps=config.video_fps,
                        vnc_streamer=vnc_streamer,
                    )
                    screen_recorder.start()
                else:
                    screen_recorder = None

                response_raw = requests.post(
                    f"http://{config.env_server_addr}:{config.env_server_port}/task/reset",
                    json=PlaygroundResetRequest(task_config=task_config).model_dump(),
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "submitted"
                wait_finish()
                response_raw = requests.get(
                    f"http://{config.env_server_addr}:{config.env_server_port}/task/result",
                )
                response = PlaygroundResultResponse(**response_raw.json())
                # TODO: handle failed reset
                assert response.status == "finished" and response.result == "success"

                instruction = task_config["instruction"]
                logger.info(f"Task instruction: {instruction}")
            else:
                if task_config["visual"]:
                    screen_recorder = ScreenRecorder(
                        fps=config.video_fps,
                    )
                    screen_recorder.start()
                else:
                    screen_recorder = None
                comb = evaluator_router(task_config)
                comb.reset()

                instruction = task_config["instruction"]
                logger.info(f"Task instruction: {instruction}")

            agent.reset(instruction=instruction)
            # Loop until the task is done or the max step is reached.
            for t in range(config.max_step):
                logger.info(f"Step {t}")
                if task_config["visual"]:
                    assert screen_recorder is not None
                    obs = screen_recorder.get_current_frame()
                else:
                    obs = None
                agent.generate_action(obs)
                if config.need_human_confirmation:
                    confirmed, _ = confirm_action()(lambda: True)()
                else:
                    confirmed = True
                _, done = agent.step_action(confirmed)
                time.sleep(config.minimal_action_interval)
                if done:
                    break

            task_trajectory_path = (
                Path(record_path) / task_config["task_id"]
            )
            task_trajectory_path.mkdir(parents=True, exist_ok=True)
            if task_config["visual"]:
                assert screen_recorder is not None
                screen_recorder.stop()
                screen_recorder.wait_exit()
                video_path = (task_trajectory_path / "video.mp4").as_posix()
                screen_recorder.save(video_path, 0)
                screen_recorder = None
                logger.info(f"Video saved to {video_path}")
            else:
                video_path = None

            if config.remote:
                response_raw = requests.post(
                    f"http://{config.env_server_addr}:{config.env_server_port}/task/eval",
                    json=PlaygroundEvalRequest(
                        task_config=task_config,
                    ).model_dump(),
                )
                response = PlaygroundResponse(**response_raw.json())
                assert response.status == "submitted"
                wait_finish()
                response_raw = requests.get(
                    f"http://{config.env_server_addr}:{config.env_server_port}/task/result"
                )
                response = PlaygroundResultResponse(**response_raw.json())
                assert response.status == "finished" and isinstance(response.message, dict)
                score, feedback = response.message["score"], response.message["feedback"]
            else:
                logger.info("Start evaluation")
                score, feedback = comb()

            scores[task_id] = score
            if score == 1.0:
                logger.info(f"[Result] (PASS): {feedback}")
            else:
                logger.info(f"[Result] (FAIL): {feedback}")
            export_trajectories(
                agent=agent,
                task_config=task_config,
                trajectory=agent.trajectory,
                record_path=record_path,
                score=score,
                feedback=feedback,
            )
        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback

            logger.error(f"[Unhandled Error] {repr(e)}]")
            logger.error(traceback.format_exc())
        finally:
            if screen_recorder is not None:
                screen_recorder.stop()
                screen_recorder.wait_exit()
                screen_recorder = None
            if vnc_streamer is not None:
                vnc_streamer.stop()
                vnc_streamer = None
    agent.close()
    logger.info(
        f"Average score: {sum(scores.values()) / max(len(scores), 1)}"
    )


def eval(args) -> None:
    """Evaluate the agent on the given tasks."""

    agent, record_path = setup_agent(args)
    task_configs = setup_tasks(args)

    match args.env:
        case "desktop":
            if not config.headless:
                eval_gui(agent, task_configs, record_path)
            else:
                eval_headless(agent, task_configs, record_path)
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
