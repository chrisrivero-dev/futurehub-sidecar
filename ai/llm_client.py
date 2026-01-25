# ai/llm_client.py
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

def generate_llm_response(
    prompt: str | None = None,
    system_prompt: str | None = None,
    user_message: str | None = None,
):
    if prompt is None:
        prompt = f"{system_prompt}\n\n{user_message}"

    """
    Returns:
      {
        "text": str,
        "model": str,
        "llm_used": bool
      }
    Raises RuntimeError if OPENAI_API_KEY missing.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        # HARD FAIL so you never silently ship canned thinking it's LLM.
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")

    logger.info("LLM_CALL_START model=%s prompt_len=%s", model, len(prompt))

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful customer support assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    text = (resp.choices[0].message.content or "").strip()
    logger.info("LLM_CALL_OK model=%s out_len=%s", model, len(text))

    return {"text": text, "model": model, "llm_used": True}
