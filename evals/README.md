# AgentStudio Benchmark Suites

## Evaluation on GUI Grounding

```bash
python evals/process_gui_grounding.py
```

```bash
python evals/caption_gui_grounding.py
```

```bash
python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/cogvlm2-llama3-chat-19B --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata_screenspot.jsonl


torchrun \
    --nproc_per_node=2 \
    --nnodes=${WORLD_SIZE:-1} \
    --node_rank=${RANK:-0} \
    --master_addr=${MASTER_ADDR:-127.0.0.1} \
    --master_port=${MASTER_PORT:-12345} \
    evals/eval_grounding.py \
    --checkpoint /mnt/data/public/ckpt/Qwen-VL-Chat \
    --dataset evals/datasets/gui_grounding/metadata.jsonl \
    --batch-size 16 \
    --num-workers 16


python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/paligemma-3b-mix-448 --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata.jsonl --end_idx 2
python evals/make_report.py --result_path /mnt/data/longtaozheng/agent-studio/results/gui_grounding_paligemma-3b-mix-448.jsonl

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path evals/datasets/gui_grounding/metadata.jsonl



python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/SeeClick --tokenizer /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl
python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1
python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1
python evals/main.py --provider gemini --model gemini-pro-vision --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1

python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path raw_data/mind2web/mind2web_images/metadata.jsonl --end_idx 10
python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/SeeClick --tokenizer /mnt/data/public/ckpt/Qwen-VL-Chat --eval_type gui_grounding --data_path raw_data/mind2web/mind2web_images/metadata.jsonl --end_idx 10

```
