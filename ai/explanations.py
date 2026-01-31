"""
ai/explanations.py
Pure derivation functions that explain AI decisions using existing data.
NO new classifications, NO new API calls, NO state mutations.
"""

def build_decision_explanation(intent_data, confidence_score, auto_send_decision, safety_mode, missing_info):
    """
    Generate human-readable explanation of why the AI made its recommendations.
    
    Args:
        intent_data: dict with 'primary_intent', 'secondary_intents', 'keywords'
        confidence_score: float (0-1)
        auto_send_decision: dict with 'allowed', 'reason'
        safety_mode: str ('safe', 'review_required', 'manual_only')
        missing_info: list of str (e.g., ['order_number', 'device_serial'])
    
    Returns:
        dict with explanation fields
    """
    
    # Determine confidence band
    if confidence_score >= 0.85:
        confidence_band = "high"
        confidence_desc = "High confidence - AI is very certain about intent"
    elif confidence_score >= 0.65:
        confidence_band = "medium"
        confidence_desc = "Medium confidence - some ambiguity present"
    else:
        confidence_band = "low"
        confidence_desc = "Low confidence - significant uncertainty"
    
    # Explain intent selection
    primary_intent = intent_data.get('primary_intent', 'unknown')
    keywords = intent_data.get('keywords', [])
    
    if keywords:
        why_intent = f"Detected '{primary_intent}' based on keywords: {', '.join(keywords[:3])}"
    else:
        why_intent = f"Classified as '{primary_intent}' based on message patterns"
    
    # Explain auto-send decision
    if auto_send_decision.get('allowed'):
        why_auto_send = f"Auto-send eligible: {auto_send_decision.get('reason', 'Meets safety criteria')}"
    else:
        why_auto_send = f"Auto-send blocked: {auto_send_decision.get('reason', 'Does not meet safety criteria')}"
    
    # Key signals used
    signals_used = ["intent_classification", "confidence_score"]
    if missing_info:
        signals_used.append("missing_information_detected")
    if len(intent_data.get('secondary_intents', [])) > 0:
        signals_used.append("multiple_intents_detected")
    
    # Safety mode explanation
    safety_explanations = {
        'safe': 'Response is informational and low-risk',
        'review_required': 'Response requires human review before sending',
        'manual_only': 'Issue is too complex or risky for AI assistance'
    }
    safety_explanation = safety_explanations.get(safety_mode, 'Unknown safety mode')
    
    return {
        "why_this_intent": why_intent,
        "why_auto_send_allowed_or_blocked": why_auto_send,
        "key_signals_used": signals_used,
        "confidence_band": confidence_band,
        "confidence_description": confidence_desc,
        "safety_mode": safety_mode,
        "safety_explanation": safety_explanation,
        "missing_information": missing_info or []
    }