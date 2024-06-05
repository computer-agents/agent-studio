import argparse
import itertools
import json
import os
import re
from functools import partial
from pathlib import Path

import torch
# from torchvision.ops.boxes import box_area
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

from eval_gui_grounding import parse_gui_grounding_response, eval_coord_output
from agent_studio.utils.json_utils import read_jsonl, add_jsonl


QWEN_PROMPT_TEMPLATE = """
<img>{image}</img>Please output the coordinate for the next action based on the instruction and screenshot. Your answer should be of the following format: '(X, Y)' (without quotes) where X, Y is the coordinates ranging from 0 to 1.
Instruction: {instruction}
Answer:
""".strip()  # noqa: E501


def collate_fn(batches, tokenizer):
    inputs = [example["input"] for example in batches]
    input_ids = tokenizer(inputs, return_tensors='pt', padding='longest')

    images = [example["image"] for example in batches]
    sources = [example["source"] for example in batches]
    platforms = [example["platform"] for example in batches]
    bboxes = [example["bbox"] for example in batches]
    resolutions = [example["resolution"] for example in batches]
    instructions = [example["instruction"] for example in batches]

    return input_ids.input_ids, input_ids.attention_mask, images, sources, platforms, bboxes, resolutions, instructions


class GroundGUIDataset(torch.utils.data.Dataset):
    def __init__(self, dataset, tokenizer, prompt, start_idx, end_idx):
        self.data = read_jsonl(dataset, start_idx, end_idx)
        self.data_dir = os.path.join(Path(dataset).parent, "images")
        self.tokenizer = tokenizer
        self.prompt = prompt

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        row = self.data[idx]
        image = os.path.join(self.data_dir, row["image"])
        instruction = row["instruction"]

        return {
            "input": self.prompt.format(**{"image": image, "instruction": instruction}),
            "image": row["image"],
            "source": row["source"],
            "platform": row["platform"],
            "bbox": row["bbox"],
            "resolution": row["resolution"],
            "instruction": instruction,
        }


class InferenceSampler(torch.utils.data.sampler.Sampler):
    def __init__(self, size):
        self._size = int(size)
        assert size > 0
        self._rank = torch.distributed.get_rank()
        self._world_size = torch.distributed.get_world_size()
        self._local_indices = self._get_local_indices(size, self._world_size, self._rank)

    @staticmethod
    def _get_local_indices(total_size, world_size, rank):
        shard_size = total_size // world_size
        left = total_size % world_size
        shard_sizes = [shard_size + int(r < left) for r in range(world_size)]

        begin = sum(shard_sizes[:rank])
        end = min(sum(shard_sizes[:rank + 1]), total_size)
        return range(begin, end)

    def __iter__(self):
        yield from self._local_indices

    def __len__(self):
        return len(self._local_indices)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str)
    parser.add_argument('--tokenizer', type=str, default=None)
    parser.add_argument('--dataset', type=str)
    parser.add_argument('--eval_format', type=str, default="coord", choices=["coord", "bbox"])
    parser.add_argument('--batch_size', type=int, default=1)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)
    parser.add_argument('--num_workers', type=int, default=1)
    args = parser.parse_args()

    torch.manual_seed(0)
    torch.distributed.init_process_group(
        backend='nccl',
        world_size=int(os.getenv('WORLD_SIZE', '1')),
        rank=int(os.getenv('RANK', '0')),
    )

    torch.cuda.set_device(int(os.getenv('LOCAL_RANK', 0)))

    model = AutoModelForCausalLM.from_pretrained(args.model, device_map='cuda', trust_remote_code=True).eval()

    if args.tokenizer is None:
        args.tokenizer = args.model
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True)
    tokenizer.padding_side = 'left'
    tokenizer.pad_token_id = tokenizer.eod_id

    prompt = QWEN_PROMPT_TEMPLATE

    dataset = GroundGUIDataset(
        args.dataset,
        tokenizer=tokenizer,
        prompt=prompt,
        start_idx=args.start_idx,
        end_idx=args.end_idx,
    )
    dataloader = torch.utils.data.DataLoader(
        dataset=dataset,
        sampler=InferenceSampler(len(dataset)),
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        pin_memory=True,
        drop_last=False,
        collate_fn=partial(collate_fn, tokenizer=tokenizer),
    )

    results = []
    for input_ids, attention_mask, images, sources, platforms, bboxes, resolutions, instructions in tqdm(dataloader, total=len(dataset)):
        outputs = model.generate(
            input_ids=input_ids.cuda(),
            attention_mask=attention_mask.cuda(),
            do_sample=False,
            max_new_tokens=32,
            pad_token_id=tokenizer.eod_id,
            eos_token_id=tokenizer.eod_id,
        )
        input_tokens = input_ids.shape[-1]
        output_tokens = outputs.shape[-1] - input_tokens
        responses = [tokenizer.decode(o[input_tokens:].cpu(), skip_special_tokens=True) for o in outputs]

        for image, source, platform, bbox, resolution, instruction, response in zip(images, sources, platforms, bboxes, resolutions, instructions, responses):
            results.append({
                "image": image,
                "source": source,
                "platform": platform,
                "bbox": bbox,
                "resolution": resolution,
                "instruction": instruction,
                "response": response,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            })

    torch.distributed.barrier()

    world_size = torch.distributed.get_world_size()
    merged_results = [None for _ in range(world_size)]
    torch.distributed.all_gather_object(merged_results, results)

    merged_results = [_ for _ in itertools.chain.from_iterable(merged_results)]

    if torch.distributed.get_rank() == 0:
        save_path = Path("results")
        save_path.mkdir(parents=True, exist_ok=True)
        file_stem = f"{save_path}/gui_grounding_{args.model.split('/')[-1]}"
        result_filename = Path(f"{file_stem}.jsonl")
        if args.eval_format == "coord":
            correct = total_cnt = 0
            for i, r in enumerate(merged_results):
                action = parse_gui_grounding_response(r['response'])
                score, action = eval_coord_output(action, r["bbox"], r["resolution"])
                merged_results[i].update({
                    "score": score,
                    "parsed_action": action,
                })

                add_jsonl([merged_results[i]], result_filename)
            print(f"Writing results to {result_filename}")
        # elif args.eval_format == "bbox":
        #     eval_bbox_output(merged_results)
        else:
            raise ValueError(f"Unknown eval format: {args.eval_format}")

    torch.distributed.barrier()
