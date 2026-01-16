"""
Feature Flag System
Controls AI assistant availability
"""
import os
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Feature flag definitions"""
    AI_ASSISTANT_ENABLED = "ai_assistant_enabled"


# Global flag state (default: OFF)
_FLAG_STATE = {
    FeatureFlags.AI_ASSISTANT_ENABLED: False
}


def is_enabled(flag_name, agent_id=None):
    """
    Check if a feature flag is enabled.
    
    Args:
        flag_name: Name of the flag
        agent_id: Optional agent ID for per-agent flags
    
    Returns:
        bool: True if enabled, False otherwise
    """
    # Check environment variable override
    env_key = f"FLAG_{flag_name.upper()}"
    env_value = os.getenv(env_key)
    
    if env_value is not None:
        return env_value.lower() in ('true', '1', 'yes')
    
    # Check global state
    return _FLAG_STATE.get(flag_name, False)


def set_flag(flag_name, enabled):
    """
    Set a feature flag state.
    
    Args:
        flag_name: Name of the flag
        enabled: True to enable, False to disable
    """
    _FLAG_STATE[flag_name] = enabled
    logger.info(f"Feature flag {flag_name} set to {enabled}")


def get_all_flags():
    """Get all flag states"""
    return _FLAG_STATE.copy()