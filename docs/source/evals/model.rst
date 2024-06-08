export HF_ENDPOINT=https://hf-mirror.com
./scripts/download/hfd.sh google/paligemma-3b-mix-448 --local-dir /mnt/data/public/ckpt/models--google--paligemma-3b-mix-448 --tool aria2c -x 4 --hf_username ltzheng --hf_token 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

./scripts/download/hfd.sh cckevinn/SeeClick --local-dir /mnt/data/public/ckpt/SeeClick --tool aria2c -x 4 --hf_username ltzheng --hf_token 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

./scripts/download/hfd.sh Salesforce/blip2-flan-t5-xl --local-dir /mnt/data/public/ckpt/blip2-flan-t5-xl --tool aria2c -x 4 --hf_username ltzheng --hf_token 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

./scripts/download/hfd.sh THUDM/cogvlm2-llama3-chat-19B --local-dir /mnt/data/public/ckpt/cogvlm2-llama3-chat-19B --tool aria2c -x 4

./scripts/download/hfd.sh openbmb/MiniCPM-Llama3-V-2_5 --local-dir /mnt/data/public/ckpt/MiniCPM-Llama3-V-2_5 --tool aria2c -x 4

python generate.py


python evals/mind2web_utils.py --imgs_dir /mnt/data/longtaozheng/agent-studio/raw_data/mind2web/mind2web_images


./scripts/download/hfd.sh osunlp/Multimodal-Mind2Web --local-dir /mnt/data/public/dataset/Multimodal-Mind2Web --tool aria2c -x 4 --dataset

./scripts/download/hfd.sh Writer/omniact --local-dir /mnt/data/public/dataset/omniact --tool aria2c -x 4 --dataset

./scripts/download/hfd.sh Skywork/agent-studio-data --local-dir /mnt/data/public/dataset/agent-studio-data --tool aria2c -x 4 --dataset



# Click Anything

## SFT

### Environment Setup

```bash
conda create -n click_anything python=3.11 -y
conda activate click_anything
conda install mpi4py
conda install -c conda-forge cudatoolkit-dev
export CUDA_HOME=/root/miniconda3/envs/click_anything
pip install -r requirements_ft.txt
pip install torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118
```

### Data Processing

#### Mind2Web Preprocessing

```bash
cd agent_tasks
python mind2web_process.py --imgs_dir /mnt/longtaozheng/SeeClick/mind2web_images
```

#### Fine-tune SeeClick


```bash
HF_ENDPOINT=https://hf-mirror.com python finetune/finetune.py --run_name SeeClick_mind2web_0402 --report_to "wandb" --model_max_length 704 --per_device_train_batch_size 1 --bf16 True --fix_vit False --per_device_eval_batch_size 1 --evaluation_strategy "no" --save_strategy "steps" --save_steps 500 --num_train_epochs 1 --data_path data/mind2web_train_sft.json --save_total_limit 30 --learning_rate 3e-5 --weight_decay 0.1 --adam_beta2 0.95 --warmup_ratio 0.01 --lr_scheduler_type "cosine" --logging_steps 10 --gradient_accumulation_steps 8 --use_lora --lazy_preprocess True --qwen_path Qwen/Qwen-VL-Chat --model_name_or_path cckevinn/SeeClick --cache_dir /mnt/longtaozheng/checkpoints --output_dir ./checkpoints/checkpoint_qwen/SeeClick_mind2web_0402

HF_ENDPOINT=https://hf-mirror.com torchrun --nproc_per_node 4 finetune/finetune.py --run_name SeeClick_mind2web_0403 --report_to "wandb" --model_max_length 704 --per_device_train_batch_size 1 --bf16 True --fix_vit False --per_device_eval_batch_size 1 --evaluation_strategy "no" --save_strategy "steps" --save_steps 500 --num_train_epochs 1 --data_path data/mind2web_train_sft.json --save_total_limit 30 --learning_rate 3e-5 --weight_decay 0.1 --adam_beta2 0.95 --warmup_ratio 0.01 --lr_scheduler_type "cosine" --logging_steps 10 --gradient_accumulation_steps 8 --use_lora --lazy_preprocess True --qwen_path Qwen/Qwen-VL-Chat --model_name_or_path cckevinn/SeeClick --cache_dir /mnt/longtaozheng/checkpoints --output_dir ./checkpoints/checkpoint_qwen/SeeClick_mind2web_0403

CUDA_VISIBLE_DEVICES=4,5,6,7 HF_ENDPOINT=https://hf-mirror.com python finetune/finetune.py --run_name SeeClick_mind2web_full_0404 --report_to "wandb" --model_max_length 704 --per_device_train_batch_size 1 --bf16 True --fix_vit False --per_device_eval_batch_size 1 --evaluation_strategy "no" --save_strategy "steps" --save_steps 500 --num_train_epochs 1 --data_path data/mind2web_train_sft.json --save_total_limit 30 --learning_rate 3e-5 --weight_decay 0.1 --adam_beta2 0.95 --warmup_ratio 0.01 --lr_scheduler_type "cosine" --logging_steps 10 --gradient_accumulation_steps 8 --deepspeed finetune/ds_config_zero2.json --lazy_preprocess True --qwen_path Qwen/Qwen-VL-Chat --model_name_or_path cckevinn/SeeClick --cache_dir /mnt/longtaozheng/checkpoints --output_dir ./checkpoints/checkpoint_qwen/SeeClick_mind2web_full_0404
```

* `data-path`: sft data generated in the above step
* `qwen-ckpt`: origin Qwen-VL ckpt path for loading tokenizer
* `pretrain-ckpt`: base model for fine-tuning, e.g. SeeClick-pretrain or Qwen-VL
* `save-path`: directory to save training checkpoints

#### Fine-tune SeeClick

```bash
bash finetune/finetune_lora_ds.sh --save-name SeeClick_test --max-length 704 --micro-batch-size 4 --save-interval 500 
    --train-epochs 10 --nproc-per-node 2 --data-path data/aitw_train_sft.json --learning-rate 3e-5 
    --gradient-accumulation-steps 8 --qwen-ckpt Qwen/Qwen-VL-Chat --pretrain-ckpt cckevinn/SeeClick
    --save-path xxxx/checkpoint_qwen --report_to wandb --run_name 
```
* `data-path`: sft data generated in the above step
* `qwen-ckpt`: origin Qwen-VL ckpt path for loading tokenizer
* `pretrain-ckpt`: base model for fine-tuning, e.g. SeeClick-pretrain or Qwen-VL
* `save-path`: directory to save training checkpoints

The fine-tuning scripts are similar to Qwen-VL, except for we use LoRA to fine-tune customized parameters, as in `finetune/finetune.py lines 315-327`.
This scripts fine-tune pre-train LVLM with LoRA and multi-GPU training; for more option like full-finetuning, Q-LoRA and single-GPU training, please refer to [Qwen-VL](https://github.com/QwenLM/Qwen-VL/tree/master?tab=readme-ov-file#finetuning).
