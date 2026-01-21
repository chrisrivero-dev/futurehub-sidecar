import os
from dotenv import load_dotenv
from openai import OpenAI

# ✅ Ensure env vars are loaded BEFORE client creation
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. LLM calls will not work in dev."
    )

_client = OpenAI(api_key=api_key)


def generate_llm_response(*, system_prompt: str, user_message: str) -> str:
    print("🔥 LLM CALLED (DEV)")

    response = _client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()
