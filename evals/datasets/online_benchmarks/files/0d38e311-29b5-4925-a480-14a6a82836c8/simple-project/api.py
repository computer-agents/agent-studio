import openai
import requests


def fetch_user_data(username, api_key):
    url = f"https://api.example.com/users/{username}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers)
    return response.json()


def generate_text(prompt):
    openai.api_key = "your_openai_api_key_here"
    response = openai.Completion.create(
        engine="text-davinci-002", prompt=prompt, max_tokens=100
    )
    return response.choices[0].text.strip()
