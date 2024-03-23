from agent_studio.utils.json_utils import read_jsonl

# data = read_jsonl("data/trajectories/gemini-pro/direct/gcalendar.jsonl")
# data = read_jsonl("data/trajectories/gpt-4-0125-preview/direct/gcalendar.jsonl")
data = read_jsonl("data/trajectories/gpt-3.5-turbo-0125/direct/gcalendar.jsonl")
scores = [entry["score"] for entry in data]
self_eval_scores = [entry["self_eval"]["score"] for entry in data]

# calculate true positive, false positive, true negative, false negative
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

print(f"Average score: {round(sum(scores) / len(scores), 3)}")
print(f"True positive: {tp}")
print(f"False positive: {fp}")
print(f"True negative: {tn}")
print(f"False negative: {fn}")
# print(f"Precision: {tp / (tp + fp)}")
# print(f"Recall: {tp / (tp + fn)}")
# print(f"F1 score: {round(2 * tp / (2 * tp + fp + fn), 3)}")
print(f"Accuracy: {round((tp + tn) / (tp + tn + fp + fn), 3)}")
