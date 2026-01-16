# utils/sidecar_storage.py

"""
Sidecar response storage utilities
Handles persistence of sidecar requests/responses to database
Day 2 scope: Store responses, update status fields only
"""

from datetime import datetime
from typing import Optional, Dict, Any
from models import db, Ticket
from integrations.sidecar_client import SidecarResponse
import json
import logging

logger = logging.getLogger(__name__)


def store_sidecar_response(
    ticket_id: int,
    response: SidecarResponse,
    conversation_id: Optional[str] = None
) -> bool:
    """
    Store sidecar response data to ticket
    
    Args:
        ticket_id: Ticket ID
        response: SidecarResponse from sidecar_client
        conversation_id: Optional conversation ID for tracking
        
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return False
        
        # Update status based on response
        if response.success:
            ticket.sidecar_status = 'completed'
            ticket.sidecar_error = None
        elif response.timed_out:
            ticket.sidecar_status = 'timeout'
            ticket.sidecar_error = response.error
        else:
            ticket.sidecar_status = 'failed'
            ticket.sidecar_error = response.error
        
        # Update timestamps
        ticket.sidecar_last_request = datetime.utcnow()
        ticket.ai_last_activity = datetime.utcnow()
        
        # Store conversation ID if provided
        if conversation_id:
            ticket.ai_conversation_id = conversation_id
        
        db.session.commit()
        logger.info(f"Stored sidecar response for ticket {ticket_id}: {ticket.sidecar_status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store sidecar response for ticket {ticket_id}: {str(e)}")
        db.session.rollback()
        return False


def update_sidecar_status(ticket_id: int, status: str, error: Optional[str] = None) -> bool:
    """
    Update sidecar status for a ticket
    
    Args:
        ticket_id: Ticket ID
        status: New status ('idle', 'processing', 'completed', 'failed', 'timeout')
        error: Optional error message
        
    Returns:
        True if updated successfully, False otherwise
    """
    valid_statuses = ['idle', 'processing', 'completed', 'failed', 'timeout']
    if status not in valid_statuses:
        logger.error(f"Invalid sidecar status: {status}")
        return False
    
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return False
        
        ticket.sidecar_status = status
        ticket.sidecar_error = error
        
        if status == 'processing':
            ticket.sidecar_last_request = datetime.utcnow()
        
        ticket.ai_last_activity = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Updated sidecar status for ticket {ticket_id}: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update sidecar status for ticket {ticket_id}: {str(e)}")
        db.session.rollback()
        return False


def get_sidecar_status(ticket_id: int) -> Optional[Dict[str, Any]]:
    """
    Get sidecar status for a ticket
    
    Args:
        ticket_id: Ticket ID
        
    Returns:
        Dictionary with status info or None if not found
    """
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            return None
        
        return {
            'status': ticket.sidecar_status or 'idle',
            'error': ticket.sidecar_error,
            'last_request': ticket.sidecar_last_request.isoformat() if ticket.sidecar_last_request else None,
            'conversation_id': ticket.ai_conversation_id,
            'ai_enabled': ticket.ai_assistant_enabled
        }
        
    except Exception as e:
        logger.error(f"Failed to get sidecar status for ticket {ticket_id}: {str(e)}")
        return None


def clear_sidecar_data(ticket_id: int) -> bool:
    """
    Clear sidecar data for a ticket (reset to idle)
    
    Args:
        ticket_id: Ticket ID
        
    Returns:
        True if cleared successfully, False otherwise
    """
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return False
        
        ticket.sidecar_status = 'idle'
        ticket.sidecar_error = None
        ticket.sidecar_last_request = None
        ticket.ai_conversation_id = None
        
        db.session.commit()
        logger.info(f"Cleared sidecar data for ticket {ticket_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear sidecar data for ticket {ticket_id}: {str(e)}")
        db.session.rollback()
        return False
    # utils/sidecar_storage.py - MODIFICATION ONLY
# Add auto-send eligibility evaluation and storage

# Add this import at the top
from utils.auto_send_evaluator import evaluate_from_sidecar_response, log_evaluation

# REPLACE the existing store_sidecar_response function with this version:

def store_sidecar_response(
    ticket_id: int,
    response: SidecarResponse,
    conversation_id: Optional[str] = None
) -> bool:
    """
    Store sidecar response data to ticket
    Day 6: Now includes auto-send eligibility evaluation
    
    Args:
        ticket_id: Ticket ID
        response: SidecarResponse from sidecar_client
        conversation_id: Optional conversation ID for tracking
        
    Returns:
        True if stored successfully, False otherwise
    """
    try:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            logger.error(f"Ticket {ticket_id} not found")
            return False
        
        # Update status based on response
        if response.success:
            ticket.sidecar_status = 'completed'
            ticket.sidecar_error = None
            
            # Day 6: Evaluate auto-send eligibility (evaluation only, no execution)
            if response.data:
                eligible, reason = evaluate_from_sidecar_response(
                    sidecar_response=response.data,
                    ticket_data={
                        'status': ticket.status,
                        'has_attachments': False,  # TODO: Add attachment tracking
                        'description': ticket.description
                    }
                )
                
                # Store eligibility result
                ticket.auto_send_eligible = eligible
                ticket.auto_send_reason = reason
                ticket.auto_send_evaluated_at = datetime.utcnow()
                
                # Log evaluation
                log_evaluation(ticket_id, eligible, reason)
            
        elif response.timed_out:
            ticket.sidecar_status = 'timeout'
            ticket.sidecar_error = response.error
            ticket.auto_send_eligible = False
            ticket.auto_send_reason = "Sidecar timeout - cannot evaluate"
            ticket.auto_send_evaluated_at = datetime.utcnow()
            
        else:
            ticket.sidecar_status = 'failed'
            ticket.sidecar_error = response.error
            ticket.auto_send_eligible = False
            ticket.auto_send_reason = "Sidecar analysis failed"
            ticket.auto_send_evaluated_at = datetime.utcnow()
        
        # Update timestamps
        ticket.sidecar_last_request = datetime.utcnow()
        ticket.ai_last_activity = datetime.utcnow()
        
        # Store conversation ID if provided
        if conversation_id:
            ticket.ai_conversation_id = conversation_id
        
        db.session.commit()
        logger.info(f"Stored sidecar response for ticket {ticket_id}: {ticket.sidecar_status}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to store sidecar response for ticket {ticket_id}: {str(e)}")
        db.session.rollback()
        return False