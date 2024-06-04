import argparse
from pathlib import Path

from gui_grounding_eval import GUIGroundingEval

from agent_studio.llm import setup_model
from agent_studio.utils.json_utils import add_jsonl


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
    file_stem = f"{save_path}/{args.eval_type}_{args.model.split('/')[-1]}"
    result_filename = Path(f"{file_stem}.jsonl")

    match args.eval_type:
        case "gui_grounding":
            evaluator = GUIGroundingEval(
                model=model,
                data_path=args.data_path,
                start_idx=args.start_idx,
                end_idx=args.end_idx,
            )
        case _:
            raise Exception(f"Unrecoginized eval type: {args.eval_type}")

    if args.tokenizer is None:
        args.tokenizer = args.model
    results = evaluator(args.model, args.tokenizer, args.num_workers)
    add_jsonl(results, result_filename)
    print(f"Writing results to {result_filename}")


if __name__ == "__main__":
    main()
