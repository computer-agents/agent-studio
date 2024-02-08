import time

from playground.env.desktop_env.recorder.agent_recorder import AgentRecorder
from playground.llm.openai import OpenAIProvider
from playground.llm.utils import encode_image


def test_gpt4v():
    llm = OpenAIProvider()
    recorder = AgentRecorder(record_path="playground_data/trajectories/test")
    recorder.reset(task_id=0, instruction="111")
    recorder.start()
    time.sleep(1)
    recorder.stop()
    image = recorder.get_screenshot()
    base64_image = encode_image(image)
    response, info = llm.generate_response(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": base64_image}},
                ],
            }
        ],
        model="gpt-4-vision-preview",
    )
    print("response:", response)
    print("info:", info)
