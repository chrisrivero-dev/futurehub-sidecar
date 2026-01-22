import os
import traceback
from dotenv import load_dotenv
from openai import OpenAI

# -------------------------------------
# Environment setup (load ONCE)
# -------------------------------------
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not set. LLM calls will not work in dev."
    )

client = OpenAI(api_key=api_key)

# -------------------------------------
# LLM call wrapper (HARD FAIL, NO SILENCE)
# -------------------------------------
def generate_llm_response(*, system_prompt: str, user_message: str) -> str:
    print("🔥 LLM_CLIENT HIT")

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("LLM returned empty content")

        print("🔥 LLM_CLIENT RETURNING RESPONSE")
        return content.strip()

    except Exception as e:
        print("❌ LLM_CLIENT EXCEPTION")
        traceback.print_exc()
        raise
