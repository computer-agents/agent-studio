# pytest -s tests/test_models/test_gemini.py
def test_gemini():
    from agent_studio.llm.gemini import GeminiProvider

    model = GeminiProvider()
    print(
        model.generate_response(
            messages=[{"role": "system", "content": "Hello world!"}]
        ),
        model="gemini-pro",
    )
