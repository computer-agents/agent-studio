import argparse
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from agent_studio.agent import setup_agent
from agent_studio.config.config import Config
from agent_studio.envs.desktop_env.evaluators.evaluator_helper import evaluator_router
from agent_studio.envs.desktop_env.recorder.screen_recorder import ScreenRecorder
from agent_studio.utils.json_utils import export_trajectories, read_json

config = Config()

logger = logging.getLogger("agent_studio")
format = "%(asctime)s\t%(levelname)s %(filename)s:%(lineno)s -- %(message)s"
formatter = logging.Formatter(format)
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
handler.setFormatter(formatter)
logger.addHandler(handler)
file_handler = logging.FileHandler(
    filename=os.path.join("logs", f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"),
    mode="w",
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logging.basicConfig(level=logging.DEBUG, handlers=[handler, file_handler])
logger.propagate = False


def eval(args) -> None:
    # Setup agent
    agent = setup_agent(
        agent_name=args.agent,
        model=args.model,
        remote=args.remote,
        runtime_server_addr=args.runtime_server_addr,
        runtime_server_port=args.runtime_server_port,
    )
    log_dir = f"{args.log_dir}/{args.model}/{args.agent}"
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Setup tasks
    task_configs = read_json(args.task_configs_path, args.start_idx, args.end_idx)

    # Run evaluation
    scores = {}
    # screen_recorder: ScreenRecorder | None = None
    # vnc_streamer: VNCStreamer | None = None
    # remote_server_addr = f"http://{args.runtime_server_addr}:{args.runtime_server_port}"  # noqa: E501
    # TODO: if visual, start a screen recorder (if remote, start a vnc streamer)
    for task_config in tqdm(task_configs, desc="Evaluating tasks"):
        try:
            task_id = task_config["task_id"]
            if args.remote:
                pass
                # response_raw = requests.post(f"{remote_server_addr}/runtime/reset")
                # response = AgentStudioStatusResponse(**response_raw.json())
                # assert (
                #     response.status == "success"
                # ), f"Fail to reset runtime: {response_raw.text}"
                # if task_config["visual"]:
                #     vnc_streamer = VNCStreamer(
                #         runtime_server_addr=config.runtime_server_addr,
                #         vnc_port=config.vnc_port,
                #         vnc_password=config.vnc_password,
                #     )
                #     vnc_streamer.start()
                #     screen_recorder = VNCRecorder(
                #         fps=config.video_fps,
                #         vnc_streamer=vnc_streamer,
                #     )
                #     screen_recorder.start()
                # else:
                #     screen_recorder = None

                # response_raw = requests.post(
                #     f"{remote_server_addr}/task/reset",
                #     json=AgentStudioResetRequest(task_config=task_config).model_dump(),
                # )
                # response = AgentStudioStatusResponse(**response_raw.json())
                # response = wait_finish(is_eval=False, response=response)
                # if not (
                #     response.status == "finished" and response.content == "success"
                # ):
                #     raise ValueError(f"Fail to reset task: {response.message}")

            else:
                # Record the screen as observation
                if task_config["visual"]:
                    screen_recorder = ScreenRecorder(fps=config.video_fps)
                    screen_recorder.start()
                else:
                    screen_recorder = None

                # Setup evaluators
                evaluators = evaluator_router(task_config)
                evaluators.reset()

            instruction = task_config["instruction"]
            logger.info(f"Task instruction: {instruction}")
            if "GMAIL_RECIPIENT" in instruction:
                gmail_recipient = config.gmail_recipient
                assert len(gmail_recipient) > 0, "GMAIL_RECIPIENT is not set."
                instruction = instruction.replace("GMAIL_RECIPIENT", gmail_recipient)

            # Reset the agent
            agent.reset(task_config=task_config)
            # Loop until the task is done or the max step is reached.
            for t in range(task_config["max_steps"]):
                logger.info(f"Step {t}")
                if task_config["visual"]:
                    assert screen_recorder is not None
                    obs = screen_recorder.get_current_frame()
                else:
                    obs = None
                action = agent.generate_action(obs=obs, model_name=args.model)
                if config.need_human_confirmation:
                    confirmed = (
                        input(f"Action:\n{action}\nConfirm action (y/n): ")
                        .strip()
                        .lower()
                        == "y"
                    )
                else:
                    confirmed = True
                _, done = agent.step_action(confirmed)
                time.sleep(config.min_action_interval)
                if done:
                    break

            task_trajectory_path = Path(log_dir) / task_config["task_id"]
            video_meta = None
            if task_config["visual"]:
                task_trajectory_path.mkdir(parents=True, exist_ok=True)
                assert screen_recorder is not None
                screen_recorder.stop()
                screen_recorder.wait_exit()
                video_path = (task_trajectory_path / "video.mp4").as_posix()
                video_meta = screen_recorder.save(video_path, 0)
                del screen_recorder
                screen_recorder = None
                logger.info(f"Video saved to {video_path}")

            if args.remote:
                pass
                # response_raw = requests.post(
                #     f"{remote_server_addr}/task/eval",
                #     json=AgentStudioEvalRequest(
                #         task_config=task_config,
                #         trajectory=str(jsonpickle.encode(agent.trajectory)),
                #     ).model_dump(),
                # )
                # response = AgentStudioStatusResponse(**response_raw.json())
                # response = wait_finish(is_eval=True, response=response)
                # if not (
                #     response.status == "finished" and isinstance(response.message, dict)  # noqa: E501
                # ):
                #     raise ValueError(f"Fail to evaluate task: {response.message}")
                # score, feedback = (
                #     response.message["score"],
                #     response.message["feedback"],
                # )
            else:
                logger.info("Start evaluation")
                score, feedback = evaluators()

            scores[task_id] = score
            if score == 1.0:
                logger.info(f"[Result] (PASS): {feedback}")
            else:
                logger.info(f"[Result] (FAIL): {feedback}")

            export_trajectories(
                task_config=task_config,
                trajectory=agent.trajectory,
                record_path=log_dir,
                score=score,
                feedback=feedback,
                token_count=agent.get_token_count(),
                video_meta=video_meta,
                jsonl_name=os.path.basename(args.task_configs_path).replace(
                    ".json", ".jsonl"
                ),
            )
        except Exception as e:
            import traceback

            logger.error(f"[Unhandled Error] {repr(e)}]")
            logger.error(traceback.format_exc())
        finally:
            if screen_recorder is not None:
                screen_recorder.stop()
                screen_recorder.wait_exit()
                screen_recorder = None
            # if vnc_streamer is not None:
            #     vnc_streamer.stop()
            #     vnc_streamer = None
    agent.close()
    logger.info(
        f"Average score: {sum(scores.values())}/{len(scores)}="
        f"{sum(scores.values()) / max(len(scores), 1)}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Model name")
    parser.add_argument("--agent", type=str, default="direct", help="Agent type")
    parser.add_argument("--task_configs_path", type=str, help="Path to the task config")
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)
    parser.add_argument(
        "--log_dir",
        type=str,
        default="logs",
        help="Path to save the logs",
    )
    parser.add_argument("--remote", action="store_true", help="Run in remote mode")
    parser.add_argument(
        "--runtime_server_addr",
        type=str,
        default="localhost",
        help="Remote runtime server address",
    )
    parser.add_argument(
        "--runtime_server_port",
        type=int,
        default=5900,
        help="Remote runtime server port",
    )
    args = parser.parse_args()
    logger.info(f"Running with args: {args}")
    assert args.task_configs_path is not None, "Task config is not set."

    eval(args)


if __name__ == "__main__":
    main()
