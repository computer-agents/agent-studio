import os
import re
from pathlib import Path
from typing import Any
import logging

from common import map_with_progress

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl, add_jsonl
from schema import Action, InverseAction

logger = logging.getLogger("eval_logger")

QUERY_TEMPLATE = """
Answer the following multiple choice question. The last line of your response should be of the following format: 'Answer: $LETTER' (without quotes) where LETTER is one of {choices}. Think step by step before answering. For example, if there'are three options "A: type\nB: click\nC: scroll", and you think the executed action is "click", then your response should be "Answer: B".

You are given two sequential images which denotes the observation before and after an action respectively, and the action is one of the steps to finish the insuruction. Your task is to determine the executed action type between the two observations. 
Instruction: {instruction}

{choices_str}
""".strip()  # noqa: E501

# {''.join([chr(65 + i) for i in range(len(choices))])}
ANSWER_PATTERN = r"(?i)Answer\s*:\s*([A-Z])"


def format_idm_prompt(
    data_dir: str,
    instruction: str,
    action: Action,
    action_space: list[str],
) -> list:
    messages = [
        # {"role": "user", "content": QUERY_TEMPLATE.format(instruction=episode.instruction, action_space=", ".join(list(get_action_space())))},
    ]
    if action.obs_before is not None and action.obs_after is not None:
        messages.append({"role": "user", "content": Path(data_dir, action.obs_before)})
        messages.append({"role": "user", "content": Path(data_dir, action.obs_after)})
    choicestr = "\n".join([f"{chr(65 + i)}. {action}" for i, action in enumerate(list(action_space))])
    choices = ''.join([chr(65 + i) for i in range(len(action_space))])
    messages.append({"role": "user", "content": QUERY_TEMPLATE.format(instruction=instruction, choices_str=choicestr, choices=choices)})

    return messages


def eval_idm_response(response: str, reference: str) -> float:
    try:
        match = re.search(ANSWER_PATTERN, response.splitlines()[-1])
    except:
        match = None
    return 1.0 if (match and match.group(1).strip().startswith(reference)) else 0.0


class IDMEval:
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
        self.error_filename = result_filename.with_suffix(".error.jsonl")
        self.num_workers = num_workers

    def __call__(
        self, model_name: str, tokenizer_name: str,
    ) -> list[dict[str, Any]]:
        def fn(row: dict):
            try:
                action: InverseAction = InverseAction.model_validate(row)
                if action.obs_before is None or action.obs_after is None:
                    raise ValueError("obs_before and obs_after must be provided")

                # Query the model and evaluate the response
                prompt = format_idm_prompt(self.data_dir, action.instruction, action, action.action_space)
                response, info = self.model.generate_response(
                    prompt, model=model_name, tokenizer=tokenizer_name,
                    do_sample=False, max_length=32, num_return_sequences=1,
                )
                # get the position in the set of action_space
                index = action.action_space.index(action.operation)
                ref_answer = chr(65 + index)

                score = eval_idm_response(response, ref_answer)

                result = {
                    "obs_before": action.obs_before,
                    "obs_after": action.obs_after,
                    "action_space": action.action_space,
                    "score": score,
                    "source": action.source,
                    "platform": action.platform,
                    "annotation_id": action.action_id,
                    "instruction": action.instruction,
                    "response": response,
                    "ref_answer": action.operation,
                    # "parsed_action": action,
                    "input_tokens": info.get("prompt_tokens", 0),
                    "output_tokens": info.get("completion_tokens", 0),
                }
                add_jsonl([result], self.result_filename)
                logger.info(f"Writing results {action.action_id} to {self.result_filename}")
            except Exception as e:
                logger.error(f"[Error processing action: {action.action_id}]: {e}")
                add_jsonl([row], self.error_filename)

        map_with_progress(fn, self.data, self.num_workers)
