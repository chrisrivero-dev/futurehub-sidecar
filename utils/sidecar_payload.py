# utils/sidecar_payload.py

"""
Sidecar request payload builder
Constructs standardized payloads for sidecar service
Day 3: Build request payload from ticket + message data
"""

from typing import Dict, Any, Optional, List
from models import Ticket, Reply
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def build_ticket_payload(ticket: Ticket, include_history: bool = False) -> Dict[str, Any]:
    """
    Build sidecar request payload from ticket
    
    Args:
        ticket: Ticket model instance
        include_history: Whether to include reply history
        
    Returns:
        Dictionary payload for sidecar service
    """
    payload = {
        'ticket_id': ticket.id,
        'subject': ticket.subject or '',
        'description': ticket.description or '',
        'customer': {
            'email': ticket.customer_email or '',
            'name': ticket.customer_name or ''
        },
        'metadata': {
            'status': ticket.status,
            'priority': ticket.priority,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'source': 'email'  # Default source
        }
    }
    
    # Include reply history if requested
    if include_history:
        replies = Reply.query.filter_by(ticket_id=ticket.id).order_by(Reply.created_at.asc()).all()
        payload['history'] = [
            {
                'author': reply.author_name or reply.author_email,
                'message': reply.message,
                'timestamp': reply.created_at.isoformat() if reply.created_at else None
            }
            for reply in replies
        ]
    
    return payload


def build_analysis_request(ticket: Ticket) -> Dict[str, Any]:
    """
    Build analysis request for new ticket
    Used during ticket creation
    
    Args:
        ticket: Ticket model instance
        
    Returns:
        Complete request payload for sidecar /analyze endpoint
    """
    return {
        'action': 'analyze',
        'ticket': build_ticket_payload(ticket, include_history=False),
        'options': {
            'generate_suggestions': True,
            'extract_entities': True,
            'classify_intent': True,
            'assess_sentiment': True
        }
    }


def build_reply_request(
    ticket: Ticket,
    draft_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build reply generation request
    Future use: For generating draft replies
    
    Args:
        ticket: Ticket model instance
        draft_message: Optional existing draft to refine
        
    Returns:
        Complete request payload for sidecar /reply endpoint
    """
    payload = {
        'action': 'generate_reply',
        'ticket': build_ticket_payload(ticket, include_history=True)
    }
    
    if draft_message:
        payload['draft'] = draft_message
    
    return payload


def validate_payload(payload: Dict[str, Any]) -> bool:
    """
    Validate sidecar payload has required fields
    
    Args:
        payload: Request payload dictionary
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required top-level fields
        if 'action' not in payload:
            logger.error("Payload missing 'action' field")
            return False
        
        if 'ticket' not in payload:
            logger.error("Payload missing 'ticket' field")
            return False
        
        # Check required ticket fields
        ticket = payload['ticket']
        required_ticket_fields = ['ticket_id', 'subject', 'description']
        
        for field in required_ticket_fields:
            if field not in ticket:
                logger.error(f"Ticket payload missing '{field}' field")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Payload validation error: {str(e)}")
        return False