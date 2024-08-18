import uuid

from agent_studio.utils.json_utils import add_jsonl, read_json

source_path = "data/tasks/gdocs.json"
target_path = "data/tasks/gdocs.jsonl"

data = read_json(source_path)
results = []

# replace empty id with uuid
for i in range(len(data)):
    if (
        "task_id" not in data[i]
        or isinstance(data[i]["task_id"], int)
        or data[i]["task_id"] is None
    ):
        task_id = str(uuid.uuid4())
        # sort the keys
        results.append(
            {
                "task_id": task_id,
                "instruction": (
                    data[i]["instruction"]
                    if "instruction" in data[i]
                    else data[i]["intent"]
                ),
                "evals": data[i]["evals"],
                "visual": data[i]["visual"] if "visual" in data[i] else False,
            }
        )

add_jsonl(results, target_path, mode="w")

print("Done!")
