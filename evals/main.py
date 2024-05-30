import argparse
from pathlib import Path

from common import make_report
from gui_grounding_eval import GUIGroundingEval

from agent_studio.llm import setup_model
from agent_studio.utils.json_utils import add_json


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", type=str, default=None)
    parser.add_argument("--eval_type", type=str, default=None)
    parser.add_argument("--data_path", type=str, default=None)
    parser.add_argument("--start_idx", type=int, default=0)
    parser.add_argument("--end_idx", type=int, default=None)
    parser.add_argument("--num_workers", type=int, default=1)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    print(f"Running with args: {args}")

    model = setup_model(args.provider)

    match args.eval_type:
        case "gui_grounding":
            evaluator = GUIGroundingEval(
                provider=args.provider,
                data_path=args.data_path,
                start_idx=args.start_idx,
                end_idx=args.end_idx,
            )
        case _:
            raise Exception(f"Unrecoginized eval type: {args.eval_type}")

    result = evaluator(model, args.num_workers)
    metrics = result.metrics | {"score": result.score}
    print(metrics)
    save_path = Path("results")
    save_path.mkdir(parents=True, exist_ok=True)
    file_stem = f"{save_path}/{args.eval_type}_{args.provider.split('/')[-1]}"
    report_filename = f"{file_stem}.html"
    print(f"Writing report to {report_filename}")
    with open(report_filename, "w") as fh:
        fh.write(make_report(result))
    result_filename = Path(f"{file_stem}.jsonl")
    add_json(metrics, result_filename)
    print(f"Writing results to {result_filename}")


if __name__ == "__main__":
    main()
