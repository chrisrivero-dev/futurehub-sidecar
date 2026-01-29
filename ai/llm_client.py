# ai/llm_client.py
import os
import logging
from openai import OpenAI
from openai import AuthenticationError, OpenAIError

logger = logging.getLogger(__name__)

def generate_llm_response(
    prompt: str | None = None,
    system_prompt: str | None = None,
    user_message: str | None = None,
):
    """
    Single, authoritative LLM entrypoint.
    Always returns a dict with at least { "text": str }.
    Never raises OpenAI-related exceptions.
    """

    # -----------------------------
    # Build prompt
    # -----------------------------
    if prompt is None:
        if not system_prompt or not user_message:
            return {
                "error": "invalid_prompt",
                "text": "⚠️ Missing prompt information.",
                "llm_used": False,
            }
        prompt = f"{system_prompt}\n\n{user_message}"

    # -----------------------------
    # API key guard
    # -----------------------------
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "error": "auth_error",
            "text": "⚠️ AI service not configured. Please check API key.",
            "llm_used": False,
        }

    model = (
        os.getenv("OPENAI_MODEL")
        or os.getenv("LLM_MODEL")
        or "gpt-4o-mini"
    )

    logger.info(
        "LLM_CALL_START model=%s prompt_len=%s",
        model,
        len(prompt),
    )

    # -----------------------------
    # OpenAI call (GUARDED)
    # -----------------------------
    try:
        client = OpenAI(api_key=api_key)

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful customer support assistant.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
        )

        text = (resp.choices[0].message.content or "").strip()

        logger.info(
            "LLM_CALL_OK model=%s out_len=%s",
            model,
            len(text),
        )

        return {
            "text": text,
            "model": model,
            "llm_used": True,
        }

    except AuthenticationError as e:
        logger.exception("LLM auth error")
        return {
            "error": "auth_error",
            "text": "⚠️ AI service authentication failed.",
            "llm_used": False,
        }

    except OpenAIError as e:
        logger.exception("LLM OpenAI error")
        return {
            "error": "llm_error",
            "text": "⚠️ AI service temporarily unavailable.",
            "llm_used": False,
        }

    except Exception as e:
        logger.exception("LLM unknown error")
        return {
            "error": "unknown_error",
            "text": "⚠️ Unexpected AI error.",
            "llm_used": False,
        }
