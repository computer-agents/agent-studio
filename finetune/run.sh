pip install -e .
pip install jsonpickle peft

export WANDB_API_KEY='ed5069227da5d2bfc22ddd654a7f3a2b87475c1f'

export CUDA_DEVICE_MAX_CONNECTIONS=1

GPUS_PER_NODE=8
NNODES=1
NODE_RANK=0
MASTER_ADDR=localhost
MASTER_PORT=6001

DISTRIBUTED_ARGS="
    --nproc_per_node $GPUS_PER_NODE \
    --nnodes $NNODES \
    --node_rank $NODE_RANK \
    --master_addr $MASTER_ADDR \
    --master_port $MASTER_PORT
"

torchrun $DISTRIBUTED_ARGS finetune/finetune.py \
    --model_name_or_path /mnt/data/public/ckpt/Qwen-VL-Chat \
    --data_path finetune/gui_grounding_train/sft_train_org.jsonl \
    --output_dir /mnt/data/public/ckpt/AgentStudio \
    --bf16 True \
    --fix_vit False \
    --run_name agent_studio_sft \
    --num_train_epochs 1 \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --per_device_eval_batch_size 1 \
    --evaluation_strategy "no" \
    --save_strategy "steps" \
    --save_steps 2000 \
    --save_total_limit 30 \
    --learning_rate 3e-5 \
    --weight_decay 0.1 \
    --adam_beta2 0.95 \
    --warmup_ratio 0.01 \
    --lr_scheduler_type "cosine" \
    --logging_steps 10 \
    --report_to "wandb" \
    --model_max_length 768 \
    --lazy_preprocess True \
    --use_lora \
    --gradient_checkpointing \
    --deepspeed finetune/ds_config_zero2.json
