"""
Draft Generation Module
Template-based response generation for support tickets
"""

def generate_draft(classification, customer_name=None, metadata=None):
    """
    Generate draft response based on intent classification.
    
    Args:
        classification: Intent classification result dict
        customer_name: Optional customer name for personalization
        metadata: Optional metadata dict (product, order_number, etc.)
    
    Returns:
        dict with draft text and metadata
    """
    intent = classification["primary_intent"]
    safety_mode = classification["safety_mode"]
    attempted_actions = classification["attempted_actions"]
    tone_modifier = classification["tone_modifier"]
    
    # Determine draft type
    draft_type = determine_draft_type(intent, safety_mode, attempted_actions)
    
    # Select and populate template
    if draft_type == "escalation":
        draft_text = generate_escalation_draft(
            classification, customer_name, metadata
        )
    elif safety_mode == "unsafe":
        draft_text = generate_diagnostic_draft(
            classification, customer_name, metadata
        )
    elif intent == "unknown_vague":
        draft_text = generate_clarification_draft(
            classification, customer_name, metadata
        )
    else:
        draft_text = generate_safe_draft(
            classification, customer_name, metadata
        )
    
    # Add tone adjustment if needed
    if tone_modifier == "panic":
        draft_text = add_panic_reassurance(draft_text, customer_name)
    
    # Calculate quality metrics
    quality_metrics = calculate_quality_metrics(draft_text, intent)
    
    # Determine canned response recommendation
    canned_response = recommend_canned_response(intent, safety_mode)
    
    return {
        "type": draft_type,
        "response_text": draft_text,
        "quality_metrics": quality_metrics,
        "canned_response_suggestion": canned_response
    }


def determine_draft_type(intent, safety_mode, attempted_actions):
    """Determine what type of draft to generate"""
    # If customer tried 3+ steps, escalate
    if len(attempted_actions) >= 3:
        return "escalation"
    
    # Unsafe intents = clarification only
    if safety_mode == "unsafe":
        return "clarification_only"
    
    # Unknown/vague = clarification
    if intent == "unknown_vague":
        return "clarification_only"
    
    # Safe intents = full draft
    return "full"


def generate_diagnostic_draft(classification, customer_name, metadata):
    """Generate clarification draft for diagnostic issues (unsafe intents)"""
    intent = classification["primary_intent"]
    attempted_actions = classification["attempted_actions"]
    
    # Get device name
    device = get_device_name(metadata)
    
    # Get issue description
    issue_desc = get_issue_description(intent)
    
    # Build greeting
    greeting = f"Thanks for reaching out"
    if customer_name:
        greeting = f"Thanks for reaching out, {customer_name}"
    
    # Build acknowledgment
    acknowledgment = f"I understand your {device} {issue_desc} — that's definitely something we need to resolve."
    
    # Acknowledge attempted steps if any
    attempted_text = ""
    if attempted_actions:
        actions_list = format_actions_list(attempted_actions)
        attempted_text = f"\n\nI see you've already tried {actions_list} — good troubleshooting."
    
    # Build diagnostic request based on intent
    diagnostic_request = get_diagnostic_request(intent)
    
    # Build closing
    closing = "An agent will review these details and provide specific troubleshooting steps within 4 hours."
    
    return f"{greeting}. {acknowledgment}{attempted_text}\n\n{diagnostic_request}\n\n{closing}"


def generate_escalation_draft(classification, customer_name, metadata):
    """Generate escalation draft when customer tried 3+ steps"""
    intent = classification["primary_intent"]
    attempted_actions = classification["attempted_actions"]
    
    # Build greeting
    greeting = "Thanks for the detailed information"
    if customer_name:
        greeting = f"Thanks for the detailed information, {customer_name}"
    
    # Format attempted actions
    actions_list = format_actions_list(attempted_actions)
    
    # Build acknowledgment
    acknowledgment = f"I can see you've already tried {actions_list} — that's thorough troubleshooting and shows this issue needs deeper investigation."
    
    # Build diagnostic request
    diagnostic_request = get_diagnostic_request(intent)
    
    # Build closing
    closing = "An agent will analyze these and determine the specific cause so we can skip straight to the solution rather than more trial-and-error."
    
    return f"{greeting}.\n\n{acknowledgment}\n\nSince the problem persists after these steps, can you provide:\n\n{diagnostic_request}\n\n{closing}"


def generate_clarification_draft(classification, customer_name, metadata):
    """Generate clarification draft for vague/unclear issues"""
    # Build greeting
    greeting = "Thanks for reaching out"
    if customer_name:
        greeting = f"Thanks for reaching out, {customer_name}"
    
    # Build acknowledgment
    acknowledgment = "I want to make sure I understand your situation correctly."
    
    # Build clarification question
    clarification = """Can you tell me which of these describes what's happening:

• Your Apollo isn't powering on at all
• It's powered on but showing 0 H/s (not mining)
• It's mining but slower than expected
• Something else

Once I know which category this fits, I can give you the right next steps."""
    
    return f"{greeting}.\n\n{acknowledgment}\n\n{clarification}"


def generate_safe_draft(classification, customer_name, metadata):
    """Generate full draft for safe intents"""
    intent = classification["primary_intent"]
    
    if intent == "shipping_status":
        return generate_shipping_draft(customer_name, metadata)
    elif intent == "setup_help":
        return generate_setup_draft(customer_name, metadata)
    elif intent == "general_question":
        return generate_general_question_draft(customer_name, metadata)
    elif intent == "warranty_rma":
        return generate_warranty_draft(customer_name, metadata)
    else:
        # Fallback
        return generate_generic_safe_draft(customer_name)


def generate_shipping_draft(customer_name, metadata):
    """Generate shipping status draft"""
    order_number = metadata.get("order_number") if metadata else None
    
    greeting = "Hi"
    if customer_name:
        greeting = f"Hi {customer_name}"
    
    if order_number:
        # With order number - agent needs to look up
        return f"""{greeting},

I'll need to look up your order details to give you an accurate status. An agent will check your order #{order_number} and respond with tracking information within 2 hours.

In the meantime, typical Apollo shipping timeframes are 3-5 business days from order date."""
    else:
        # No order number - ask for it
        return f"""{greeting},

I can help you track your order. To look up your shipping status, I'll need your order number (it starts with "FBT-" and was in your confirmation email).

Once you provide that, an agent can give you the exact tracking information and delivery timeline."""


def generate_setup_draft(customer_name, metadata):
    """Generate setup help draft"""
    device = get_device_name(metadata)
    
    greeting = "Thanks for reaching out"
    if customer_name:
        greeting = f"Thanks for reaching out, {customer_name}"
    
    return f"""{greeting}.

For setting up your {device}, I'll need to know a bit more about what you're trying to configure:

• Are you setting up for solo mining or pool mining?
• Do you have a specific pool in mind, or need recommendations?

Once I know this, I can provide the exact steps for your setup."""


def generate_general_question_draft(customer_name, metadata):
    """Generate educational response draft"""
    greeting = "Great question"
    if customer_name:
        greeting = f"Great question, {customer_name}"
    
    return f"""{greeting}.

To give you the most helpful answer, could you clarify what aspect you're most interested in? For example:

• How the technology works
• Which option is better for your situation
• What the practical differences are

This will help me tailor the explanation to what you need."""


def generate_warranty_draft(customer_name, metadata):
    """Generate warranty/RMA process draft"""
    greeting = "Thanks for reaching out"
    if customer_name:
        greeting = f"Thanks for reaching out, {customer_name}"
    
    return f"""{greeting}.

I understand you're having issues with your device. To help you with warranty coverage or a potential RMA:

• Can you describe what's happening with the device?
• When did you receive it?
• Have you tried any troubleshooting steps?

An agent will review your specific situation and explain your options within 4 hours."""


def generate_generic_safe_draft(customer_name):
    """Fallback for safe intents"""
    greeting = "Thank you for contacting us"
    if customer_name:
        greeting = f"Thank you for contacting us, {customer_name}"
    
    return f"""{greeting}.

An agent will review your message and respond with the information you need within 4 hours."""


def add_panic_reassurance(draft_text, customer_name):
    """Add immediate reassurance for panic tone"""
    reassurance = "I understand this is urgent and you need help right away."
    if customer_name:
        reassurance = f"{customer_name}, I understand this is urgent and you need help right away."
    
    # Insert after greeting
    lines = draft_text.split("\n")
    if len(lines) > 0:
        lines.insert(1, f"\n{reassurance}\n")
        return "\n".join(lines)
    
    return draft_text


def get_device_name(metadata):
    """Extract device name from metadata"""
    if not metadata or not isinstance(metadata, dict):
        return "Apollo"
    
    product = metadata.get("product", "")
    if not product:
        return "Apollo"
    
    product_lower = product.lower()
    
    if "solo node" in product_lower:
        return "Solo Node"
    elif "apollo iii" in product_lower or "apollo3" in product_lower:
        return "Apollo III"
    elif "apollo ii" in product_lower or "apollo2" in product_lower:
        return "Apollo II"
    else:
        return "Apollo"


def get_issue_description(intent):
    """Get short issue description for acknowledgment"""
    descriptions = {
        "not_hashing": "isn't hashing",
        "sync_delay": "is having sync issues",
        "firmware_issue": "is having firmware issues",
        "performance_issue": "is having performance issues"
    }
    return descriptions.get(intent, "is having issues")


def get_diagnostic_request(intent):
    """Get diagnostic data request based on intent"""
    
    if intent == "not_hashing":
        return """To help diagnose this, can you provide:

• Your debug.log file
  (Settings → Logs → Download)
  
• Output from: bitcoin-cli getblockchaininfo"""
    
    elif intent == "sync_delay":
        return """To confirm progress is happening, can you run:

• bitcoin-cli getblockchaininfo

And let me know what block number you see?"""
    
    elif intent == "firmware_issue":
        return """To help diagnose this, can you provide:

• What firmware version you're currently on (if accessible)
• Any error messages you're seeing
• What you were doing when the issue started"""
    
    elif intent == "performance_issue":
        return """To help diagnose this, can you provide:

• How often the restarts are happening
• Your debug.log file (Settings → Logs → Download)
• Any pattern you've noticed (time of day, specific actions, etc.)"""
    
    else:
        return """To help diagnose this, can you provide:

• Your debug.log file
• A description of what you were doing when the issue started"""


def format_actions_list(actions):
    """Format attempted actions as readable list"""
    action_names = {
        "restart": "restarting",
        "firmware_update": "updating firmware",
        "pool_change": "changing pools",
        "check_logs": "checking logs"
    }
    
    readable_actions = [action_names.get(a, a) for a in actions]
    
    if len(readable_actions) == 1:
        return readable_actions[0]
    elif len(readable_actions) == 2:
        return f"{readable_actions[0]} and {readable_actions[1]}"
    else:
        return ", ".join(readable_actions[:-1]) + f", and {readable_actions[-1]}"


def recommend_canned_response(intent, safety_mode):
    """Recommend canned response by category"""
    if safety_mode == "unsafe":
        recommendations = {
            "not_hashing": {
                "category": "Node Not Hashing Troubleshooting",
                "reason": "Intent is not_hashing. Canned response contains step-by-step troubleshooting.",
                "timing": "after_diagnostic_review"
            },
            "sync_delay": {
                "category": "Node Sync Troubleshooting",
                "reason": "Intent is sync_delay. Canned response contains sync troubleshooting steps.",
                "timing": "after_diagnostic_review"
            },
            "firmware_issue": {
                "category": "Firmware Update Instructions",
                "reason": "Intent is firmware_issue. Canned response contains recovery procedures.",
                "timing": "after_diagnostic_review"
            },
            "performance_issue": {
                "category": "Performance Diagnostics",
                "reason": "Intent is performance_issue. Canned response contains diagnostic procedures.",
                "timing": "after_diagnostic_review"
            }
        }
        return recommendations.get(intent)
    
    return None  # No canned response for safe intents


def calculate_quality_metrics(draft_text, intent):
    """Calculate draft quality metrics"""
    # Structure check
    has_greeting = any(word in draft_text.lower()[:50] for word in ["thanks", "hi", "thank you", "great"])
    has_body = len(draft_text) > 100
    has_closing = "agent will" in draft_text.lower() or "once i know" in draft_text.lower()
    
    structure_score = (
        (0.33 if has_greeting else 0) +
        (0.34 if has_body else 0) +
        (0.33 if has_closing else 0)
    )
    
    # Source grounding (not implemented yet - placeholder)
    source_grounding = 0.0
    
    # Reasoning clarity
    has_explanation = any(word in draft_text.lower() for word in ["to help", "so we can", "this will"])
    reasoning_clarity = 0.80 if has_explanation else 0.60
    
    # Tone appropriateness
    has_empathy = any(word in draft_text.lower() for word in ["understand", "see you've", "i can see"])
    tone_appropriateness = 0.90 if has_empathy else 0.70
    
    # Hallucination risk (check for specific claims without sources)
    has_specific_dates = any(char.isdigit() for char in draft_text) and "within" not in draft_text.lower()
    hallucination_risk = 0.30 if has_specific_dates else 0.05
    
    # Already-tried avoidance (assume good for now)
    already_tried_avoidance = 1.0
    
    return {
        "structure_score": round(structure_score, 2),
        "source_grounding": source_grounding,
        "reasoning_clarity": reasoning_clarity,
        "tone_appropriateness": tone_appropriateness,
        "hallucination_risk": hallucination_risk,
        "already_tried_avoidance": already_tried_avoidance
    }
