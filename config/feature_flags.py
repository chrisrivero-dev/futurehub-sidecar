# config/feature_flags.py

"""
Feature flag system for FutureHub
All flags default to OFF for safety
"""

from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime


class FeatureFlag(Enum):
    """Available feature flags"""
    AI_ASSISTANT = "ai_assistant"
    SIDECAR_INTEGRATION = "sidecar_integration"
    AUTO_SEND = "auto_send"  # Future use
    EMAIL_INGESTION = "email_ingestion"  # Future use


@dataclass
class FlagConfig:
    """Configuration for a single feature flag"""
    enabled: bool
    description: str
    enabled_at: Optional[datetime] = None
    enabled_by: Optional[str] = None


class FeatureFlags:
    """
    Feature flag manager
    Centralized control for experimental features
    """
    
    # Default configuration - ALL FLAGS OFF
    _flags: Dict[FeatureFlag, FlagConfig] = {
        FeatureFlag.AI_ASSISTANT: FlagConfig(
            enabled=False,
            description="Enable AI assistant panel in ticket detail"
        ),
        FeatureFlag.SIDECAR_INTEGRATION: FlagConfig(
            enabled=False,
            description="Enable sidecar service integration"
        ),
        FeatureFlag.AUTO_SEND: FlagConfig(
            enabled=False,
            description="Enable auto-send recommendations (requires AI_ASSISTANT)"
        ),
        FeatureFlag.EMAIL_INGESTION: FlagConfig(
            enabled=False,
            description="Enable inbound email processing"
        ),
    }
    
    @classmethod
    def is_enabled(cls, flag: FeatureFlag) -> bool:
        """Check if a feature flag is enabled"""
        return cls._flags.get(flag, FlagConfig(enabled=False, description="")).enabled
    
    @classmethod
    def enable(cls, flag: FeatureFlag, enabled_by: str = "system") -> None:
        """Enable a feature flag"""
        if flag in cls._flags:
            cls._flags[flag].enabled = True
            cls._flags[flag].enabled_at = datetime.utcnow()
            cls._flags[flag].enabled_by = enabled_by
    
    @classmethod
    def disable(cls, flag: FeatureFlag) -> None:
        """Disable a feature flag"""
        if flag in cls._flags:
            cls._flags[flag].enabled = False
            cls._flags[flag].enabled_at = None
            cls._flags[flag].enabled_by = None
    
    @classmethod
    def get_all(cls) -> Dict[str, dict]:
        """Get all feature flags and their status"""
        return {
            flag.value: {
                "enabled": config.enabled,
                "description": config.description,
                "enabled_at": config.enabled_at.isoformat() if config.enabled_at else None,
                "enabled_by": config.enabled_by
            }
            for flag, config in cls._flags.items()
        }
    
    @classmethod
    def check_dependencies(cls, flag: FeatureFlag) -> bool:
        """
        Check if required dependencies are enabled
        Returns False if dependencies are not met
        """
        dependencies = {
            FeatureFlag.AUTO_SEND: [FeatureFlag.AI_ASSISTANT],
        }
        
        required = dependencies.get(flag, [])
        return all(cls.is_enabled(dep) for dep in required)