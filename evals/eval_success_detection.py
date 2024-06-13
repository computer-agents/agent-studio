import os
import re
from pathlib import Path
from typing import Any
import logging

from common import map_with_progress

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl, add_jsonl
from schema import Episode

logger = logging.getLogger("eval_logger")

QUERY_TEMPLATE = """
You are a human annotator, your task is to judge whether the instruction is correctly executed based on the above trajectory. The trajectory is represented by a sequence of actions and the observations before and after each action. Your response is either "Answer: succ" if the trajectory finished the instruction or "Answer: fail" if not.
The action space: {action_space}
Instruction: {instruction}
""".strip()  # noqa: E501

ANSWER_PATTERN = r"(?i)Answer\s*:\s*(succ|fail)"


def format_success_detection_prompt(
    data_dir: str,
    episode: Episode,
) -> list:
    messages = [
    ]
    for action in episode.actions:
        if action.obs_before is not None:
            messages.append({"role": "user", "content": Path(os.path.join(data_dir, action.obs_before))})
        messages.append({"role": "user", "content": f'{action.metadata["repr"]}'})
    if action.obs_after is not None:
        messages.append({"role": "user", "content": Path(os.path.join(data_dir, action.obs_after))})
    messages.append(
        {"role": "user", "content": QUERY_TEMPLATE.format(instruction=episode.instruction, action_space=", ".join(episode.action_space))},
    )

    return messages


def parse_success_detection_response(response: str, reference: bool) -> float:
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except:
        match = None
    return 1.0 if (match and ((match.group(1) == "succ")) == reference) else 0.0


class SuccessDetectionEval:
    def __init__(
        self,
        model: BaseModel,
        data_path: str,
        result_filename: Path,
        start_idx: int = 0,
        end_idx: int | None = None,
        num_workers: int = 1,
    ):
        self.model = model
        self.data = read_jsonl(data_path, start_idx, end_idx)
        self.data_dir = os.path.join(Path(data_path).parent, "images")
        self.result_filename = result_filename
        self.num_workers = num_workers

    def __call__(
        self, model_name: str, tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        def fn(row: dict):
            episode: Episode = Episode.model_validate(row)
            # only use the last 5 actions
            episode.actions = episode.actions[-5:] if len(episode.actions) > 5 else episode.actions

            # Query the model and evaluate the response
            prompt = format_success_detection_prompt(self.data_dir, episode)
            response, info = self.model.generate_response(
                prompt, model=model_name, tokenizer=tokenizer_name,
                do_sample=False, max_new_tokens=32, num_return_sequences=1,
            )
            logger.info(f"response: {response}")
            score = parse_success_detection_response(response, episode.is_success)

            result = {
                "trajectory_images": [action.obs_before for action in episode.actions] + ([episode.actions[-1].obs_after] if episode.actions[-1].obs_after else []),
                "trajectory_actions": [action.metadata["repr"] for action in episode.actions],
                "instruction": episode.instruction,
                "score": score,
                "source": episode.source,
                "platform": episode.platform,
                "annotation_id": episode.annotation_id,
                "ref_answer": episode.is_success,
                # "resolution": row["resolution"],
                "response": response,
                # "parsed_action": action,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }

            add_jsonl([result], self.result_filename)
            logger.info(f"Writing results {episode.annotation_id} to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
