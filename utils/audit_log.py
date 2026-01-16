# utils/audit_log.py

"""
Audit logging for FutureHub
Logs critical actions with timestamps and context
Day 5: Agent approval logging for AI draft sends
"""

from datetime import datetime
from typing import Optional, Dict, Any
import logging
import json

logger = logging.getLogger(__name__)


class AuditLog:
    """
    Audit logging utility
    Logs actions to application log and optionally to database
    """
    
    @staticmethod
    def log_ai_draft_approval(
        ticket_id: int,
        agent_email: str,
        draft_message: str,
        confidence: Optional[float] = None,
        intent: Optional[str] = None
    ) -> None:
        """
        Log agent approval of AI-generated draft
        
        Args:
            ticket_id: Ticket ID
            agent_email: Email of agent who approved
            draft_message: Draft message that was approved
            confidence: AI confidence score (if available)
            intent: Classified intent (if available)
        """
        log_entry = {
            'action': 'ai_draft_approved',
            'timestamp': datetime.utcnow().isoformat(),
            'ticket_id': ticket_id,
            'agent_email': agent_email,
            'draft_length': len(draft_message),
            'confidence': confidence,
            'intent': intent
        }
        
        logger.info(f"AUDIT: AI draft approved for ticket {ticket_id} by {agent_email}")
        logger.debug(f"AUDIT_DETAIL: {json.dumps(log_entry)}")
    
    @staticmethod
    def log_ai_draft_rejected(
        ticket_id: int,
        agent_email: str,
        reason: Optional[str] = None
    ) -> None:
        """
        Log agent rejection of AI-generated draft
        
        Args:
            ticket_id: Ticket ID
            agent_email: Email of agent who rejected
            reason: Optional reason for rejection
        """
        log_entry = {
            'action': 'ai_draft_rejected',
            'timestamp': datetime.utcnow().isoformat(),
            'ticket_id': ticket_id,
            'agent_email': agent_email,
            'reason': reason
        }
        
        logger.info(f"AUDIT: AI draft rejected for ticket {ticket_id} by {agent_email}")
        logger.debug(f"AUDIT_DETAIL: {json.dumps(log_entry)}")
    
    @staticmethod
    def log_manual_reply(
        ticket_id: int,
        agent_email: str,
        message_length: int
    ) -> None:
        """
        Log manual reply (non-AI)
        
        Args:
            ticket_id: Ticket ID
            agent_email: Email of agent who sent reply
            message_length: Length of manual message
        """
        log_entry = {
            'action': 'manual_reply',
            'timestamp': datetime.utcnow().isoformat(),
            'ticket_id': ticket_id,
            'agent_email': agent_email,
            'message_length': message_length
        }
        
        logger.info(f"AUDIT: Manual reply sent for ticket {ticket_id} by {agent_email}")
        logger.debug(f"AUDIT_DETAIL: {json.dumps(log_entry)}")
    
    @staticmethod
    def log_send_error(
        ticket_id: int,
        agent_email: str,
        error: str,
        ai_generated: bool = False
    ) -> None:
        """
        Log send error
        
        Args:
            ticket_id: Ticket ID
            agent_email: Email of agent who attempted send
            error: Error message
            ai_generated: Whether message was AI-generated
        """
        log_entry = {
            'action': 'send_error',
            'timestamp': datetime.utcnow().isoformat(),
            'ticket_id': ticket_id,
            'agent_email': agent_email,
            'error': error,
            'ai_generated': ai_generated
        }
        
        logger.error(f"AUDIT: Send error for ticket {ticket_id} by {agent_email}: {error}")
        logger.debug(f"AUDIT_DETAIL: {json.dumps(log_entry)}")