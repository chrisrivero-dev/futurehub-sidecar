# services/ticket_service.py

"""
Ticket service layer
Handles ticket creation with optional sidecar integration
Day 3: Create tickets + trigger sidecar analysis if enabled
"""

from typing import Optional, Dict, Any
from models import db, Ticket
from config.feature_flags import FeatureFlags, FeatureFlag
from integrations.sidecar_client import SidecarClient
from utils.sidecar_payload import build_analysis_request, validate_payload
from utils.sidecar_storage import update_sidecar_status, store_sidecar_response
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class TicketService:
    """
    Service layer for ticket operations
    Separates business logic from routes
    """
    
    def __init__(self):
        # Initialize sidecar client if needed
        sidecar_url = os.getenv('SIDECAR_URL', 'http://localhost:8001')
        self.sidecar_client = SidecarClient(base_url=sidecar_url)
    
    def create_ticket(
        self,
        subject: str,
        description: str,
        customer_email: str,
        customer_name: Optional[str] = None,
        priority: str = 'medium',
        status: str = 'open',
        ai_assistant_enabled: Optional[bool] = None
    ) -> Ticket:
        """
        Create new ticket with optional sidecar analysis
        
        Sidecar analysis is triggered IF:
        1. Feature flag is enabled
        2. ai_assistant_enabled is True (or None and flag is ON)
        3. Payload validation passes
        
        Sidecar failure does NOT block ticket creation
        
        Args:
            subject: Ticket subject
            description: Ticket description/body
            customer_email: Customer email
            customer_name: Optional customer name
            priority: Ticket priority (low/medium/high)
            status: Ticket status (default: open)
            ai_assistant_enabled: Override for AI assistant (None = use feature flag)
            
        Returns:
            Created Ticket instance
        """
        # Create ticket first
        ticket = Ticket(
            subject=subject,
            description=description,
            customer_email=customer_email,
            customer_name=customer_name,
            priority=priority,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Determine if AI assistant should be enabled
        if ai_assistant_enabled is None:
            # Use feature flag default
            ai_assistant_enabled = FeatureFlags.is_enabled(FeatureFlag.AI_ASSISTANT)
        
        ticket.ai_assistant_enabled = ai_assistant_enabled
        ticket.sidecar_status = 'idle'
        
        # Commit ticket to DB first (non-blocking)
        try:
            db.session.add(ticket)
            db.session.commit()
            logger.info(f"Created ticket {ticket.id}: {subject}")
        except Exception as e:
            logger.error(f"Failed to create ticket: {str(e)}")
            db.session.rollback()
            raise
        
        # Trigger sidecar analysis if enabled
        if ai_assistant_enabled and FeatureFlags.is_enabled(FeatureFlag.SIDECAR_INTEGRATION):
            self._trigger_sidecar_analysis(ticket)
        else:
            logger.info(f"Sidecar analysis skipped for ticket {ticket.id} (AI disabled or feature flag OFF)")
        
        return ticket
    
    def _trigger_sidecar_analysis(self, ticket: Ticket) -> None:
        """
        Trigger sidecar analysis for ticket (non-blocking)
        Failures are logged but do not raise exceptions
        
        Args:
            ticket: Ticket to analyze
        """
        try:
            logger.info(f"Triggering sidecar analysis for ticket {ticket.id}")
            
            # Build request payload
            payload = build_analysis_request(ticket)
            
            # Validate payload
            if not validate_payload(payload):
                logger.error(f"Invalid sidecar payload for ticket {ticket.id}")
                update_sidecar_status(ticket.id, 'failed', 'Invalid payload')
                return
            
            # Update status to processing
            update_sidecar_status(ticket.id, 'processing')
            
            # Make sidecar request
            response = self.sidecar_client.request(
                endpoint='/analyze',
                method='POST',
                data=payload
            )
            
            # Store response
            conversation_id = None
            if response.success and response.data:
                conversation_id = response.data.get('conversation_id')
            
            store_sidecar_response(
                ticket_id=ticket.id,
                response=response,
                conversation_id=conversation_id
            )
            
            if response.success:
                logger.info(f"Sidecar analysis completed for ticket {ticket.id}")
            else:
                logger.warning(f"Sidecar analysis failed for ticket {ticket.id}: {response.error}")
        
        except Exception as e:
            # Log error but do not raise - ticket creation should succeed
            logger.error(f"Sidecar analysis error for ticket {ticket.id}: {str(e)}")
            update_sidecar_status(ticket.id, 'failed', str(e))
    
    def enable_ai_assistant(self, ticket_id: int) -> bool:
        """
        Enable AI assistant for existing ticket
        Triggers sidecar analysis if feature flag is ON
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found")
                return False
            
            ticket.ai_assistant_enabled = True
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Trigger analysis if feature flag is ON
            if FeatureFlags.is_enabled(FeatureFlag.SIDECAR_INTEGRATION):
                self._trigger_sidecar_analysis(ticket)
            
            logger.info(f"AI assistant enabled for ticket {ticket_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable AI assistant for ticket {ticket_id}: {str(e)}")
            db.session.rollback()
            return False
    
    def disable_ai_assistant(self, ticket_id: int) -> bool:
        """
        Disable AI assistant for ticket
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            ticket = Ticket.query.get(ticket_id)
            if not ticket:
                logger.error(f"Ticket {ticket_id} not found")
                return False
            
            ticket.ai_assistant_enabled = False
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"AI assistant disabled for ticket {ticket_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable AI assistant for ticket {ticket_id}: {str(e)}")
            db.session.rollback()
            return False