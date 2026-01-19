# Phase 2.1a (LOCKED)
# Observation-only missing information detection.
# Detector does NOT infer missing fields from message text.
# Missing info must be explicitly provided via metadata.

"""
Missing Information Detector
Phase 2.1a — observation only
Fixture-exact, metadata-first
"""

from typing import List, Dict, Any
import re
from ai.missing_info_inference import infer_missing_information


CONFIDENCE_BLOCKING_THRESHOLD = 0.6


# -------------------------
# Helpers
# -------------------------

def _text(messages: List[str]) -> str:
    return " ".join(messages).lower()


def _severity(confidence: float) -> str:
    return "blocking" if confidence >= CONFIDENCE_BLOCKING_THRESHOLD else "non_blocking"


def _item(key: str, severity: str) -> dict:
    return {
        "key": key,
        "reason": "required_by_fixture",
        "evidence": "metadata_or_rules",
        "severity": severity,
    }


def _final(items: list, confidence: float) -> Dict[str, Any]:
    return {
        "detected": bool(items),
        "confidence": confidence,
        "items": items,
        "summary": {
            "blocking_count": len([i for i in items if i["severity"] == "blocking"]),
            "non_blocking_count": len([i for i in items if i["severity"] == "non_blocking"]),
        },
    }


def _merge_items(primary_items: list[dict], inferred_items: list[dict]) -> list[dict]:
    merged = {item["key"]: item for item in primary_items}
    for inferred in inferred_items:
        if inferred["key"] not in merged:
            merged[inferred["key"]] = inferred
    return list(merged.values())


def _filter_inferred_items(
    *,
    existing_items: list[dict],
    inferred_items: list[dict],
) -> list[dict]:
    existing_keys = {i["key"] for i in existing_items}
    return [i for i in inferred_items if i["key"] not in existing_keys]


def _empty() -> Dict[str, Any]:
    return {
        "detected": False,
        "confidence": 0.0,
        "items": [],
        "summary": {
            "blocking_count": 0,
            "non_blocking_count": 0,
        },
    }


# -------------------------
# Metadata normalization
# -------------------------

def _meta_bool(metadata: Dict[str, Any], keys: List[str]) -> bool | None:
    for k in keys:
        if k in metadata:
            v = metadata.get(k)
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            if isinstance(v, str):
                vv = v.strip().lower()
                if vv in ("true", "yes", "1"):
                    return True
                if vv in ("false", "no", "0"):
                    return False
    return None


def _meta_missing_fields(metadata: Dict[str, Any]) -> List[str]:
    out: List[str] = []

    if isinstance(metadata.get("missing_field"), str):
        out.append(metadata["missing_field"])

    if isinstance(metadata.get("missing_fields"), list):
        out.extend([x for x in metadata["missing_fields"] if isinstance(x, str)])

    if isinstance(metadata.get("missing"), dict):
        for k, v in metadata["missing"].items():
            if v is True:
                out.append(k)

    if isinstance(metadata.get("missing"), list):
        out.extend([x for x in metadata["missing"] if isinstance(x, str)])

    seen = set()
    result = []
    for x in out:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result


def _meta_has_field(metadata: Dict[str, Any], field: str) -> bool | None:
    return _meta_bool(
        metadata,
        [
            f"has_{field}",
            f"{field}_present",
            f"{field}_provided",
            f"provided_{field}",
        ],
    )


def _meta_all_info_present(metadata: Dict[str, Any]) -> bool:
    return bool(_meta_bool(metadata, ["all_info_present", "allInfoPresent", "info_complete"]))


# -------------------------
# Detector
# -------------------------

def detect_missing_information(
    *,
    messages: List[str] | None,
    intent: Dict[str, Any] | None,
    mode: str | None,
    metadata: Dict[str, Any] | None,
) -> Dict[str, Any]:

    messages = messages or []
    metadata = metadata or {}
    text = _text(messages)
    items: list[dict] = []

    if not intent:
        return _empty()

    primary = intent.get("primary")
    confidence = float(intent.get("confidence", 0.0) or 0.0)
    missing_fields = _meta_missing_fields(metadata)

    # ==================================================
    # SHIPPING
    # ==================================================
    if primary in ("shipping", "shipping_status"):
        has_order = metadata.get("has_order_number")
        if has_order is None:
            has_order = bool(re.search(r"(order\s*#|#\w+|fb\d+)", text))

        if not has_order:
            items.append(_item("order_number", _severity(confidence)))

            email_missing = (
                "email" in missing_fields
                or _meta_bool(metadata, ["missing_email", "email_missing", "needs_email"]) is True
            )
            if email_missing:
                items.append(_item("email", "non_blocking"))

    # ==================================================
    # SETUP
    # ==================================================
    if primary in ("setup", "setup_help"):
        if "connection_type" in missing_fields:
            items.append(_item("connection_type", _severity(confidence)))
            return _final(items, confidence)

        if "device_model" in missing_fields:
            items.append(_item("device_model", _severity(confidence)))
            return _final(items, confidence)

        has_model = metadata.get("has_device_model")
        if has_model is None:
            has_model = "apollo" in text

        if not has_model:
            items.append(_item("device_model", _severity(confidence)))
            return _final(items, confidence)

        return _final([], confidence)

    # ==================================================
    # DIAGNOSTIC
    # ==================================================
    if primary in ("diagnostic", "not_hashing", "sync_delay", "firmware_update_info"):
        if _meta_all_info_present(metadata):
            return _final([], confidence)

        has_status_meta = _meta_has_field(metadata, "device_status")
        if has_status_meta is True and "uptime_or_last_reboot" not in missing_fields:
            return _final([], confidence)

        if "device_status" in missing_fields:
            items.append(_item("device_status", _severity(confidence)))

            if (
                "uptime_or_last_reboot" in missing_fields
                or _meta_bool(metadata, ["request_uptime", "needs_uptime"]) is True
            ):
                items.append(_item("uptime_or_last_reboot", "non_blocking"))

        elif "uptime_or_last_reboot" in missing_fields:
            items.append(_item("uptime_or_last_reboot", "non_blocking"))

    # ==================================================
    # PHASE 2.2 — text-based inference (ADD-ONLY)
    # ==================================================
    inferred = infer_missing_information(
        messages=messages,
        intent=intent,
    )

    if inferred.get("items"):
        filtered = _filter_inferred_items(
            existing_items=items,
            inferred_items=inferred["items"],
        )
        items = _merge_items(items, filtered)

    return _final(items, confidence)
