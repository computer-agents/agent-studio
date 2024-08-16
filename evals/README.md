# Measuring Core Agent Abilities

## Download Dataset

We curated a single-step UI grounding test dataset, GroundUI-18K and a multi-step trajectory test dataset. For efficient benchmarking, we sampled subsets from both these datasets, forming GroundUI-1K and TrajectoryLite. All datasets can be obtained in our project page.

Using these two datasets, we created a leaderboard covering three core agent abilities: UI grounding, learning from videos, and success detection. The four specific datasets for benchmarking (GroundUI-1K, IDM-Single, IDM-Multiple, and SuccessDetection) can be automatically downloaded via HuggingFace without additional operations. The GroundUI-18K dataset is also hosted on HuggingFace.

If downloading from the Google Drive link at our project page (recommended, easier for making reports):

Extract the downloaded GroundUI dataset:

```bash
tar -xvf gui_grounding.tar.gz
```

The file structure:

```
evals/
└─ datasets/
    └─ gui_grounding/
        ├─ images/
        ├─ metadata_1k.jsonl
        ├─ metadata_raw_1k.jsonl
        ├─ metadata_raw.jsonl
        └─ metadata.jsonl
```

There are 13522 screenshots under `images`. Both raw instructions and recaptioned instructions are given in the `metadata_1k.jsonl` and `metadata.jsonl`. The raw files `metadata_raw_1k` and `metadata.jsonl` consists only raw instructions. More details of recaptioning can be found at the bottom of this page.

Extract the downloaded TrajectoryLite dataset:

```bash
tar -xvf trajectory_lite.tar.gz
```

The file structure:

```
evals/
└─ datasets/
    └─ trajectory_lite/
        ├─ images/
        ├─ metadata_idm.jsonl
        ├─ metadata_idmn2n.jsonl
        └─ metadata_success_detection.jsonl
```

For raw data downloading and processing, see [the detailed instructions](processing/README.md).

We use GPT-4o to recaption GroundUI-1K.

```bash
python evals/re_caption_gui_grounding_data.py --model gpt-4o-2024-05-13 --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
```

We use CogVLM2 to recaption GroundUI-18K.

```bash
python evals/re_caption_gui_grounding_data.py --model /PATH/TO/cogvlm2-llama3-chat-19B --data_path evals/datasets/gui_grounding/metadata_raw.jsonl
```

## Evaluation on GUI Grounding

### Evaluation on re-captioned GroundUI-1K

The `--model` tested are `gpt-4o-2024-05-13`, `gpt-4-turbo-2024-04-09`, `gemini-pro-vision`, `gemini-1.5-pro-001`, `gemini-1.5-flash-001` (Vertex AI), `claude-3-5-sonnet-20240620`, `claude-3-5-sonnet@20240620` (Vertex AI), `/PATH/TO/SeeClick`, `/PATH/TO/cogvlm2-llama3-chat-19B`, `/PATH/TO/Qwen-VL-Chat`, `/PATH/TO/cogagent-chat-hf`, `/PATH/TO/paligemma-3b-mix-448`, `/PATH/TO/paligemma-3b-pt-896`, `/PATH/TO/MiniCPM-Llama3-V-2_5`.

You can add `--num_workers` to speed up the evaluation process for APIs.

For example:

```bash
# If using local data downloaded from Google Drive
python evals/main.py --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
# If using HuggingFace dataset
python evals/main.py --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path agent-studio/GroundUI-1K

# You need to specify the `--tokenizer` for some open-source models like SeeClick, otherwise the tokenizer will be automatically loaded from the model path.
python evals/main.py --model /PATH/TO/SeeClick --tokenizer /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
```

After running experiments, you can generate a report with metrics using the following command. The `--result_path` is the path to save the evaluation results shown in the last log of running evaluation, e.g., `results/gui_grounding/gpt-4o-2024-05-13.jsonl`. Example script for gathering results:

```bash
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding/gpt-4o-2024-05-13.jsonl
```

### Ablation on raw instruction

The following command ablates the performance of the model on raw instructions.

```bash
python evals/main.py --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
python evals/main.py --model /PATH/TO/SeeClick --tokenizer /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
python evals/main.py --model /PATH/TO/cogvlm2-llama3-chat-19B --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
```

### Full evaluation on GroundUI-18K

```bash
python evals/main.py --model /PATH/TO/SeeClick --tokenizer /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata.jsonl
```

## Evaluation on Inverse Action Labeling

IDM-Single: Predict a single action between two neighboring states (images).

```bash
# If using local data downloaded from Google Drive
python evals/main.py --model gpt-4o-2024-05-13 --eval_type idm --data_path evals/datasets/trajectory_lite/metadata_idm.jsonl
# If using HuggingFace dataset
python evals/main.py --model gpt-4o-2024-05-13 --eval_type idm --data_path agent-studio/IDM-Single

python evals/main.py --model /PATH/TO/Qwen-VL-Chat --eval_type idm --data_path evals/datasets/trajectory_lite/metadata_idm.jsonl
```

Example script for gathering results:

```bash
python evals/make_report.py --image_path evals/datasets/trajectory_lite/images --result_path results/idm/gpt-4o-2024-05-13.jsonl
```

IDM-Multiple: Predict all actions given a trajectory.

```bash
# If using local data downloaded from Google Drive
python evals/main.py --model gpt-4o-2024-05-13 --eval_type idmn2n --data_path evals/datasets/trajectory_lite/metadata_idmn2n.jsonl
# If using HuggingFace dataset
python evals/main.py --model gpt-4o-2024-05-13 --eval_type idmn2n --data_path agent-studio/IDM-Multiple

python evals/main.py --model /PATH/TO/Qwen-VL-Chat --eval_type idmn2n --data_path evals/datasets/trajectory_lite/metadata_idmn2n.jsonl
```

Example script for gathering results:

```bash
python evals/make_report.py --image_path evals/datasets/trajectory_lite/images --result_path results/idmn2n/gpt-4o-2024-05-13.jsonl
```

## Evaluation on Success Detection

Example script for evaluation (`success_detection` or `success_detection_actionless`):

```bash
# If using local data downloaded from Google Drive
python evals/main.py --model gpt-4o-2024-05-13 --eval_type success_detection --data_path evals/datasets/trajectory_lite/metadata_success_detection.jsonl
# If using HuggingFace dataset
python evals/main.py --model gpt-4o-2024-05-13 --eval_type success_detection --data_path agent-studio/SuccessDetection

python evals/main.py --model /PATH/TO/Qwen-VL-Chat --eval_type success_detection --data_path evals/datasets/trajectory_lite/metadata_success_detection.jsonl
```

Example script for gathering results:

```bash
python evals/make_report.py --image_path evals/datasets/trajectory_lite/images --result_path results/success_detection/gpt-4o-2024-05-13.jsonl
```
