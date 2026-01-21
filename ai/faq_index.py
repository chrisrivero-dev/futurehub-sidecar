import json
from pathlib import Path

# Single, authoritative FAQ source (LOCKED)
FAQ_PATH = Path(__file__).resolve().parent.parent / "faq" / "faq_chunks.json"


def load_faq_snippets(intent: str, max_items: int = 3) -> list[str]:
    """
    PHASE 1.4 — SAFE knowledge loader
    - Reads from faq_chunks.json only
    - Returns short official snippets by intent
    - Never raises
    """

    if not FAQ_PATH.exists():
        return []

    try:
        data = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    snippets = data.get(intent, [])
    if not isinstance(snippets, list):
        return []

    clean = []
    for s in snippets:
        if isinstance(s, str):
            clean.append(s.strip())
        if len(clean) >= max_items:
            break

    return clean
