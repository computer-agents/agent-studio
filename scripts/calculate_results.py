from agent_studio.utils.json_utils import read_jsonl

providers = ["gpt-3.5-turbo-0125", "gpt-4-0125-preview", "gemini-pro"]
apps = ["filesystem", "google", "GUI"]

for provider in providers:
    print("# Provider:", provider)
    for app in apps:
        print("## App:", app)
        if app == "google":
            data = []
            data += read_jsonl(f"data/trajectories/{provider}/direct/gcalendar.jsonl")
            data += read_jsonl(f"data/trajectories/{provider}/direct/gmail.jsonl")
            data += read_jsonl(f"data/trajectories/{provider}/direct/gdocs.jsonl")
        elif app == "filesystem":
            data = read_jsonl(f"data/trajectories/{provider}/direct/filesystem.jsonl")
        elif app == "GUI":
            data = []
            if provider == "gpt-4-0125-preview":
                data += read_jsonl(f"data/trajectories/gpt-4-vision-preview/direct/desktop_hard.jsonl")
                data += read_jsonl(f"data/trajectories/gpt-4-vision-preview/direct/vscode.jsonl")
            elif provider == "gemini-pro":
                data += read_jsonl(f"data/trajectories/gemini-pro-vision/direct/desktop_hard.jsonl")
                data += read_jsonl(f"data/trajectories/gemini-pro-vision/direct/vscode.jsonl")
            else:
                continue
        else:
            raise ValueError("Invalid app")
        scores = [entry["score"] for entry in data]
        self_eval_scores = [entry["self_eval"]["score"] for entry in data]

        tp = 0
        fp = 0
        tn = 0
        fn = 0
        for entry in data:
            if entry["score"] > 0:
                if entry["self_eval"]["score"] > 0:
                    tp += 1
                else:
                    fp += 1
            else:
                if entry["self_eval"]["score"] > 0:
                    fn += 1
                else:
                    tn += 1

        print(f"Average score: {round(sum(scores) / len(scores) * 100, 1)}")
        print(f"Total tasks: {tp + fp + tn + fn}")
        print(f"True positive: {tp}")
        print(f"False positive: {fp}")
        print(f"True negative: {tn}")
        print(f"False negative: {fn}")
        print(f"Accuracy: {round((tp + tn) / (tp + tn + fp + fn) * 100, 1)}\n")
