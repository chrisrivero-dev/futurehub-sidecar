"""
Template Bridge — Variable merging and verification for draft templates.

bridgeMetadataToTemplate(): Merge Ralph's extracted data into template placeholders.
scanAndVerifyVariables(): Detect missing variables and return verification result.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------
# Variable pattern: {{variable_name}}
# -----------------------------------------------------------
VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")

# -----------------------------------------------------------
# Known variable definitions with display labels and required flag
# -----------------------------------------------------------
KNOWN_VARIABLES: Dict[str, Dict[str, Any]] = {
    "customer_name": {
        "label": "Customer Name",
        "required": False,
        "default": "there",
    },
    "order_number": {
        "label": "Order Number",
        "required": True,
        "default": None,
    },
    "product": {
        "label": "Product Model",
        "required": False,
        "default": "Apollo",
    },
    "device_model": {
        "label": "Device Model",
        "required": False,
        "default": "Apollo",
    },
    "tracking_number": {
        "label": "Tracking Number",
        "required": True,
        "default": None,
    },
    "firmware_version": {
        "label": "Firmware Version",
        "required": False,
        "default": "latest",
    },
    "device_status": {
        "label": "Device Status",
        "required": True,
        "default": None,
    },
    "sync_percentage": {
        "label": "Sync Percentage",
        "required": False,
        "default": None,
    },
    "connection_type": {
        "label": "Connection Type",
        "required": False,
        "default": "Ethernet",
    },
    "ip_address": {
        "label": "IP Address",
        "required": False,
        "default": None,
    },
    "email": {
        "label": "Email Address",
        "required": False,
        "default": None,
    },
    "debug_log": {
        "label": "Debug Log",
        "required": True,
        "default": None,
    },
    "uptime_or_last_reboot": {
        "label": "Uptime / Last Reboot",
        "required": False,
        "default": None,
    },
}


def bridgeMetadataToTemplate(
    template_content: str,
    extracted_data: Dict[str, Any],
) -> str:
    """
    Merge extracted metadata into template placeholders.

    Replaces {{variable_name}} tokens in template_content with values
    from extracted_data. Uses defaults from KNOWN_VARIABLES when a
    non-required variable is missing.

    Args:
        template_content: Template string with {{variable}} placeholders.
        extracted_data: Dict of variable_name -> value from Ralph extraction.

    Returns:
        Merged template string. Missing required variables remain as
        {{variable_name}} so they are detectable by scanAndVerifyVariables.
    """
    if not template_content:
        return template_content

    data = extracted_data or {}

    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        value = data.get(var_name)

        if value is not None and str(value).strip():
            return str(value).strip()

        # Check for known default
        var_def = KNOWN_VARIABLES.get(var_name, {})
        default = var_def.get("default")

        if default is not None:
            return str(default)

        # Leave placeholder for required / unknown variables
        return match.group(0)

    return VARIABLE_PATTERN.sub(_replace, template_content)


def scanAndVerifyVariables(
    template_content: str,
    extracted_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Scan template for {{variable}} placeholders and verify which are
    satisfied by extracted_data.

    Returns:
        {
            "all_satisfied": bool,
            "missing": [
                {
                    "key": str,
                    "label": str,
                    "required": bool,
                }
            ],
            "satisfied": [str],
            "total_variables": int,
        }
    """
    if not template_content:
        return {
            "all_satisfied": True,
            "missing": [],
            "satisfied": [],
            "total_variables": 0,
        }

    data = extracted_data or {}
    variables_found = VARIABLE_PATTERN.findall(template_content)

    # Deduplicate while preserving order
    seen = set()
    unique_vars: List[str] = []
    for v in variables_found:
        if v not in seen:
            seen.add(v)
            unique_vars.append(v)

    satisfied: List[str] = []
    missing: List[Dict[str, Any]] = []

    for var_name in unique_vars:
        value = data.get(var_name)
        var_def = KNOWN_VARIABLES.get(var_name, {})
        has_default = var_def.get("default") is not None

        if value is not None and str(value).strip():
            satisfied.append(var_name)
        elif has_default:
            satisfied.append(var_name)
        else:
            missing.append({
                "key": var_name,
                "label": var_def.get("label", var_name.replace("_", " ").title()),
                "required": var_def.get("required", False),
            })

    # Also check missing info from metadata that aren't template variables
    # but are still required for the draft pipeline
    has_required_missing = any(m.get("required", False) for m in missing)

    return {
        "all_satisfied": len(missing) == 0,
        "missing": missing,
        "satisfied": satisfied,
        "total_variables": len(unique_vars),
        "has_required_missing": has_required_missing,
    }


def get_template_by_id(
    template_id: str,
    canned_responses: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Retrieve template content from canned_responses list by ID.
    """
    for item in canned_responses:
        if str(item.get("id")) == str(template_id):
            return item.get("content", "")
    return None


def prepare_template_draft(
    *,
    template_id: Optional[str],
    canned_responses: List[Dict[str, Any]],
    extracted_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Full pipeline: load template, merge variables, verify completeness.

    Returns:
        {
            "draft_text": str,
            "template_used": bool,
            "verification": dict,  # from scanAndVerifyVariables
        }
    """
    if not template_id:
        return {
            "draft_text": "",
            "template_used": False,
            "verification": scanAndVerifyVariables("", {}),
        }

    template_content = get_template_by_id(template_id, canned_responses)
    if not template_content:
        return {
            "draft_text": "",
            "template_used": False,
            "verification": scanAndVerifyVariables("", {}),
        }

    # First scan raw template to know what's needed
    verification = scanAndVerifyVariables(template_content, extracted_data)

    # Then merge what we have
    merged = bridgeMetadataToTemplate(template_content, extracted_data)

    return {
        "draft_text": merged,
        "template_used": True,
        "verification": verification,
    }
