import os
from openai import OpenAI

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_llm_response(*, system_prompt: str, user_message: str) -> str:
    print("🔥 LLM CALLED")

    response = _client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()
