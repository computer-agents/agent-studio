# AgentStudio Benchmark Suites

## Evaluation on GUI Grounding

```bash
python evals/process_gui_grounding.py
```

```bash
python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/Qwen--Qwen-VL-Chat --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl
python evals/main.py --provider huggingface --model /mnt/data/public/ckpt/SeeClick --tokenizer /mnt/data/public/ckpt/Qwen--Qwen-VL-Chat --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl
python evals/main.py --provider openai --model gpt-4o-2024-05-13 --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1
python evals/main.py --provider claude --model claude-3-sonnet-20240229 --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1
python evals/main.py --provider gemini --model gemini-pro-vision --eval_type gui_grounding --data_path raw_data/screenspot/metadata.jsonl --end_idx 1
```
