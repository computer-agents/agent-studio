import os
from pathlib import Path

from agent_studio.llm import BaseModel
from agent_studio.utils.json_utils import read_jsonl


class BaseEval:
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
        if data_path.endswith(".jsonl"):
            self.data = read_jsonl(data_path, start_idx, end_idx)
            self.data_dir = os.path.join(Path(data_path).parent, "images")
        else:
            from datasets import load_dataset

            dataset = load_dataset(data_path)["train"]
            # the default split is "train", but actually all data are test data
            if end_idx is not None:
                self.data = [dataset[i] for i in range(start_idx, end_idx)]
            else:
                self.data = [dataset[i] for i in range(start_idx, len(dataset))]
            self.data_dir = None

        self.result_filename = result_filename
        self.num_workers = num_workers
