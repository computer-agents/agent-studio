pip install -e .
pip install jsonpickle peft

export WANDB_API_KEY='ed5069227da5d2bfc22ddd654a7f3a2b87475c1f'

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

torchrun $DISTRIBUTED_ARGS finetune/finetune.py --run_name agent_studio_sft --report_to "wandb" --model_max_length 768 --per_device_train_batch_size 8 --bf16 True --fix_vit False --per_device_eval_batch_size 1 --evaluation_strategy "no" --save_strategy "steps" --save_steps 5000 --num_train_epochs 3 --data_path finetune/gui_grounding_train/sft_train.jsonl --save_total_limit 30 --learning_rate 3e-5 --weight_decay 0.1 --adam_beta2 0.95 --warmup_ratio 0.01 --lr_scheduler_type "cosine" --logging_steps 10 --gradient_accumulation_steps 1 --use_lora --lazy_preprocess True --model_name_or_path /mnt/data/public/ckpt/Qwen-VL-Chat --output_dir /mnt/data/public/ckpt/AgentStudio --deepspeed finetune/ds_config_zero2.json
