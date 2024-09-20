import random

from agent_studio.utils.json_utils import add_jsonl, read_jsonl


def main():
    data_path = "evals/datasets/gui_grounding/metadata_raw.jsonl"
    data = read_jsonl(data_path)

    save_path = data_path.replace("metadata_raw.jsonl", "metadata_raw_1k.jsonl")

    web_data = []
    desktop_data = []
    mobile_data = []
    for d in data:
        if d["platform"] == "web":
            web_data.append(d)
        elif d["platform"] == "desktop":
            desktop_data.append(d)
        elif d["platform"] == "mobile":
            mobile_data.append(d)
        else:
            print(d)

    print(f"Web: {len(web_data)}")
    print(f"Desktop: {len(desktop_data)}")
    print(f"Mobile: {len(mobile_data)}")
    counts = {
        "web": len(web_data),
        "desktop": len(desktop_data),
        "mobile": len(mobile_data),
    }

    # sample a 1K split (400/300/300)
    samples = {"web": 400, "desktop": 300, "mobile": 300}

    random.seed(42)
    sampled_indices = {
        platform: sorted(random.sample(range(counts[platform]), samples[platform]))
        for platform in counts
    }
    sampled_web_data = [web_data[i] for i in sampled_indices["web"]]
    sampled_desktop_data = [desktop_data[i] for i in sampled_indices["desktop"]]
    sampled_mobile_data = [mobile_data[i] for i in sampled_indices["mobile"]]

    sampled_data = sampled_web_data + sampled_desktop_data + sampled_mobile_data
    add_jsonl(sampled_data, save_path)
    print(f"Subset saved to {save_path}")


if __name__ == "__main__":
    main()
