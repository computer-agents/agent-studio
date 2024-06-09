# AgentStudio Benchmark Suites

## Env setup

```bash
conda create -n agent_studio_evals python=3.11
conda activate agent_studio_evals
pip install transformers torch einops torchvision xformers matplotlib opencv-python jsonpickle 
pip install -e .
mv agent_studio/config/api_key_template.json agent_studio/config/api_key.json
```

## Re-Caption

If use GPT-4o:

```bash
python evals/re_caption_gui_grounding_data.py --provider openai --model gpt-4o-2024-05-13 --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
```

If use CogVLM2:

```bash
python evals/re_caption_gui_grounding_data.py --provider huggingface --model ../checkpoints/cogvlm2-llama3-chat-19B --data_path evals/datasets/gui_grounding/metadata_raw.jsonl
```

## Evaluation on GUI Grounding

Ablation on raw instruction:

```bash
python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
mv results/gui_grounding_gpt-4o-2024-05-13.jsonl results/gui_grounding_gpt-4o-2024-05-13_raw_instruction.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_gpt-4o-2024-05-13_raw_instruction.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/SeeClick --tokenizer /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
mv results/gui_grounding_SeeClick.jsonl results/gui_grounding_SeeClick_raw_instruction.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_SeeClick_raw_instruction.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/cogvlm2-llama3-chat-19B --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_raw_1k.jsonl
mv results/gui_grounding_cogvlm2-llama3-chat-19B.jsonl results/gui_grounding_cogvlm2-llama3-chat-19B_raw_instruction.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_cogvlm2-llama3-chat-19B_raw_instruction.jsonl
```

Evaluation after recaptioning:

```bash
python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_gpt-4o-2024-05-13.jsonl

python evals/main.py --provider openai --model gpt-4-turbo-2024-04-09 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_gpt-4-turbo-2024-04-09.jsonl

python evals/main.py --provider gemini --model gemini-pro-vision --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_gemini-pro-vision.jsonl

python evals/main.py --provider gemini --model gemini-1.5-pro --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl

python evals/main.py --provider gemini --model gemini-1.5-flash --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl

python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl


python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/SeeClick --tokenizer /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_SeeClick.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/cogvlm2-llama3-chat-19B --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path evals/datasets/gui_grounding/images --result_path results/gui_grounding_cogvlm2-llama3-chat-19B.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path /mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images --result_path /mnt/data/longtaozheng/agent-studio/results/gui_grounding_Qwen-VL-Chat.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/cogagent-chat-hf --tokenizer /mnt/data/public/ckpt/vicuna-7b-v1.5 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path /mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images --result_path /mnt/data/longtaozheng/agent-studio/results/gui_grounding_cogagent-chat-hf.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/paligemma-3b-mix-448 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path /mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images --result_path /mnt/data/longtaozheng/agent-studio/results/gui_grounding_paligemma-3b-mix-448.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/paligemma-3b-pt-896 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path /mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images --result_path /mnt/data/longtaozheng/agent-studio/results/gui_grounding_paligemma-3b-pt-896.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/MiniCPM-Llama3-V-2_5 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_1k.jsonl
python evals/make_report.py --image_path /mnt/data/longtaozheng/agent-studio/evals/datasets/gui_grounding/images --result_path /mnt/data/longtaozheng/agent-studio/results/gui_grounding_MiniCPM-Llama3-V-2_5.jsonl

```


```bash
```



python evals/main.py --provider gemini --model gemini-pro-vision --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1



torchrun --nproc_per_node=2 \
    --nnodes=${WORLD_SIZE:-1} \
    --node_rank=${RANK:-0} \
    --master_addr=${MASTER_ADDR:-127.0.0.1} \
    --master_port=${MASTER_PORT:-12345} \
    evals/eval_gui_grounding_dist.py \
    --model /mnt/data/public/ckpt/Qwen-VL-Chat \
    --dataset evals/datasets/gui_grounding/metadata.jsonl \
    --batch_size 16 \
    --num_workers 16

```
