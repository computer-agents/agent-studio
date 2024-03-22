from agent_studio.llm.openai import OpenAIProvider


def test_gpt4v():
    llm = OpenAIProvider()
    response, info = llm.generate_response(
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                ],
            }
        ],
        model="gpt-4-vision-preview",
    )
    print("response:", response)
    print("info:", info)
