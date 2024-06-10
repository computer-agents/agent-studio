import argparse
from pathlib import Path
import time

from eval_gui_grounding import GUIGroundingEval
from eval_gui_trajectory import GUITrajectoryEval
from eval_gui_inverse import GUIInverseEval

from agent_studio.llm import setup_model


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider", type=str, choices=["openai", "gemini", "claude", "huggingface"]
    )
    parser.add_argument("--model", type=str)
    parser.add_argument("--tokenizer", type=str, default=None)
    parser.add_argument("--eval_type", type=str)
    parser.add_argument("--data_path", type=str)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)
    parser.add_argument("--num_workers", type=int, default=1)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    print(f"Running with args: {args}")

    model = setup_model(args.provider)
    save_path = Path("results")
    save_path.mkdir(parents=True, exist_ok=True)
    # with time
    file_stem = f"{save_path}/{args.eval_type}_{args.model.split('/')[-1]}_{time.strftime('%H%M%S')}"
    if args.start_idx != 0:
        file_stem += f"_start{args.start_idx}"
    if args.end_idx is not None:
        file_stem += f"_end{args.end_idx}"
    result_filename = Path(f"{file_stem}.jsonl")

    match args.eval_type:
        case "gui_grounding":
            evaluator = GUIGroundingEval(
                model=model,
                data_path=args.data_path,
                result_filename=result_filename,
                start_idx=args.start_idx,
                end_idx=args.end_idx,
                num_workers=args.num_workers,
            )
        case "gui_trajectory":
            evaluator = GUITrajectoryEval(
                model=model,
                data_path=args.data_path,
                result_filename=result_filename,
                start_idx=args.start_idx,
                end_idx=args.end_idx,
                num_workers=args.num_workers,
            )
        case "gui_inverse":
            evaluator = GUIInverseEval(
                model=model,
                data_path=args.data_path,
                result_filename=result_filename,
                start_idx=args.start_idx,
                end_idx=args.end_idx,
                num_workers=args.num_workers,
            )
        case _:
            raise Exception(f"Unrecoginized eval type: {args.eval_type}")

    if args.tokenizer is None:
        args.tokenizer = args.model

    evaluator(args.model, args.tokenizer)


if __name__ == "__main__":
    main()
