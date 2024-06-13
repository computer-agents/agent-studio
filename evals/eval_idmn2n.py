import os
import re
from pathlib import Path
from typing import Any
import logging

from common import map_with_progress

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl, add_jsonl
from schema import Action, Episode

logger = logging.getLogger("eval_logger")

QUERY_TEMPLATE = """
Answer the following multiple selection question. The last line of your response should be of the following format: 'Answer: [LETTER] -> [LETTER] -> ...' (without quotes) where each letter is one of "{choices}".

In this question, you are given the goal(instruction) of the trajectory and a sequence of images during the trajectory, which denote the observations before and after each action. You should not assume whether the trajectory is finished or not. Your task is to determine the executed action types between the observations.
For example, the instruction is "Open the browser", the action space is ["type", "click", "scroll"], and the trajectory is ["obs1_image", "obs2_image", "obs3_image"], the choices are "A: type\nB: click\nC: scroll", and you think the executed action between obs1_image and obs2_image is "type", and the executed action between obs2_image and obs3_image is "scroll", then your response should be "Answer: [A] -> [C]". Think step by step before answering.

Instruction: {instruction}

{choices_str}
""".strip()  # noqa: E501


def format_idm_prompt(
    data_dir: str,
    instruction: str,
    actions: list[Action],
    action_space: list[str],
) -> tuple[list, list, list]:
    messages = [
        # {"role": "user", "content": QUERY_TEMPLATE.format(instruction=episode.instruction, action_space=", ".join(list(get_action_space())))},
    ]
    selected_actions: list[Action] = []
    for action in actions:
        if action.obs_before is None or action.obs_after is None:
            raise ValueError(f"{action} does not have obs_before or obs_after.")
        else:
            messages.append({"role": "user", "content": Path(data_dir, action.obs_before)})
            selected_actions.append(action)
    choicestr = "\n".join([f"{chr(65 + i)}. {selected_actions}" for i, selected_actions in enumerate(list(action_space))])
    choices = ''.join([chr(65 + i) for i in range(len(action_space))])
    messages.append({"role": "user", "content": QUERY_TEMPLATE.format(instruction=instruction, choices_str=choicestr, choices=choices)})

    ref_answer = [chr(65 + action_space.index(action.operation)) for action in selected_actions]

    return messages, selected_actions, ref_answer


def eval_idm_response(response: str, reference: list) -> float:
    try:
        section_match: re.Match[str] | None = re.search(r'Answer\s*:\s*(.*)', response.splitlines()[-1])
        matched_section = section_match.group(1)
        letter_pattern = r'([A-Za-z])'
        match = re.findall(letter_pattern, matched_section)
    except:
        match = []
    score = 0.0
    for i in range(min(len(match), len(reference))):
        if match[i] == reference[i]:
            score += 1
    return score
    


class IDMN2NEval:
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
            # only use at most the last 5 actions
            if episode.actions[-1].obs_after is not None:
                episode.actions = episode.actions[-5:] if len(episode.actions) > 5 else episode.actions
            else:
                episode.actions = episode.actions[-6:-1] if len(episode.actions) > 6 else episode.actions[:-1]

            # Query the model and evaluate the response
            selected_actions: list[Action]
            prompt, selected_actions, ref_answer = format_idm_prompt(self.data_dir, episode.instruction, episode.actions, episode.action_space)
            response, info = self.model.generate_response(
                prompt, model=model_name, tokenizer=tokenizer_name,
                do_sample=False, max_length=32, num_return_sequences=1,
            )

            score = eval_idm_response(response, ref_answer)

            result = {
                "actions": [action.action_id for action in selected_actions],
                "action_space": episode.action_space,
                "score": score,
                "source": episode.source,
                "platform": episode.platform,
                "annotation_id": episode.annotation_id,
                "instruction": episode.instruction,
                "response": response,
                "ref_answer": ref_answer,
                # "parsed_action": action,
                "input_tokens": info.get("prompt_tokens", 0),
                "output_tokens": info.get("completion_tokens", 0),
            }
            add_jsonl([result], self.result_filename)
            logger.info(f"Writing results {episode.annotation_id} to {self.result_filename}")

        map_with_progress(fn, self.data, self.num_workers)
