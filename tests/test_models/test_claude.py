# pytest -s tests/test_models/test_claude.py
def test_gemini():
    from agent_studio.llm.claude import AnthropicProvider

    model = AnthropicProvider()
    print(
        model.generate_response(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "system", "content": "Hello world!"},
                {"role": "user", "content": "Hello world!"},
            ],
            temperature=0.0,
        ),
    )
