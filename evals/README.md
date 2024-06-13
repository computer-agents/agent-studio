# AgentStudio Benchmark Suites

## Re-Captioning

If use GPT-4o:

```bash
python evals/re_caption_gui_grounding_data.py --provider openai --model gpt-4o-2024-05-13 --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
```

If use CogVLM2:

```bash
python evals/re_caption_gui_grounding_data.py --provider huggingface --model /PATH/TO/cogvlm2-llama3-chat-19B --data_path evals/datasets/gui_grounding/metadata_raw.jsonl
```

## Evaluation on GUI Grounding

Ablation on raw instruction:

```bash
python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/SeeClick --tokenizer /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/cogvlm2-llama3-chat-19B --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
```

Evaluation on re-captioned GroundUI-1K dataset:

```bash
python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gpt-4o-2024-05-13.jsonl

python evals/main.py --provider openai --model gpt-4-turbo-2024-04-09 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gpt-4-turbo-2024-04-09.jsonl

python evals/main.py --provider gemini --model gemini-pro-vision --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gemini-pro-vision.jsonl

python evals/main.py --provider gemini --model gemini-1.5-pro --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gemini-1.5-pro.jsonl

python evals/main.py --provider gemini --model gemini-1.5-flash --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gemini-1.5-flash.jsonl

python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/claude-3-sonnet-20240229.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/SeeClick --tokenizer /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/SeeClick.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/cogvlm2-llama3-chat-19B --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/cogvlm2-llama3-chat-19B.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/Qwen-VL-Chat.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/cogagent-chat-hf --tokenizer /PATH/TO/vicuna-7b-v1.5 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/cogagent-chat-hf.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/paligemma-3b-mix-448 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/paligemma-3b-mix-448.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/paligemma-3b-pt-896 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/paligemma-3b-pt-896.jsonl

python evals/main.py --provider huggingface --model /PATH/TO/MiniCPM-Llama3-V-2_5 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/MiniCPM-Llama3-V-2_5.jsonl
```

Full evaluation:

```bash
python evals/main.py --provider huggingface --model /PATH/TO/SeeClick --tokenizer /PATH/TO/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw.jsonl
```

## Evaluation on Success Detection

```bash
python evals/main.py --provider huggingface --model /PATH/TO/Qwen-VL-Chat --eval_type success_detection --data_path evals/datasets/trajectory_100/metadata_success_detection.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/success_detection/Qwen-VL-Chat.jsonl

python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type success_detection --data_path evals/datasets/trajectory_100/metadata_success_detection.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/success_detection/gpt-4o.jsonl

python evals/main.py --provider gemini --model gemini-pro-vision --eval_type success_detection --data_path evals/datasets/trajectory_100/metadata_success_detection.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/success_detection/gemini-pro-vision.jsonl

python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type success_detection --data_path evals/datasets/trajectory_100/metadata_success_detection.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/success_detection/claude-3-sonnet-20240229.jsonl
```

## Evaluation on Inverse Action Labeling

Predict single action between two neighboring states (images):

```bash
python evals/main.py --provider huggingface --model /PATH/TO/Qwen-VL-Chat --eval_type idm --data_path evals/datasets/trajectory_100/metadata_idm.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idm/Qwen-VL-Chat.jsonl

python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type idm --data_path evals/datasets/trajectory_100/metadata_idm.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idm/gpt-4o-2024-05-13.jsonl

python evals/main.py --provider gemini --model gemini-pro-vision --eval_type idm --data_path evals/datasets/trajectory_100/metadata_idm.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idm/gemini-pro-vision.jsonl

python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type idm --data_path evals/datasets/trajectory_100/metadata_idm.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idm/claude-3-sonnet-20240229.jsonl
```

Predict all actions given a trajectory:

```bash
python evals/main.py --provider huggingface --model /PATH/TO/Qwen-VL-Chat --eval_type idmn2n --data_path evals/datasets/trajectory_100/metadata_idmn2n.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idmn2n/Qwen-VL-Chat.jsonl

python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type idmn2n --data_path evals/datasets/trajectory_100/metadata_idmn2n.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idmn2n/gpt-4o-2024-05-13.jsonl

python evals/main.py --provider gemini --model gemini-pro-vision --eval_type idmn2n --data_path evals/datasets/trajectory_100/metadata_idmn2n.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idmn2n/gemini-pro-vision.jsonl

python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type idmn2n --data_path evals/datasets/trajectory_100/metadata_idmn2n.jsonl
python evals/make_report.py --image_path evals/datasets/trajectory_100/images --result_path results/idmn2n/claude-3-sonnet-20240229.jsonl
```
