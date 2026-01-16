# routes/inbound_email.py - NEW FILE
# Email webhook handler for Mailgun (future priority)
# Day 3: Add hook point with service layer integration

"""
Inbound email webhook handler
Receives emails from Mailgun and creates tickets
Day 3: Service layer integration ready, webhook disabled by feature flag
"""

from flask import Blueprint, request, jsonify
from config.feature_flags import FeatureFlags, FeatureFlag
from services.ticket_service import TicketService
import logging

logger = logging.getLogger(__name__)

inbound_email_bp = Blueprint('inbound_email', __name__, url_prefix='/webhook')

ticket_service = TicketService()


@inbound_email_bp.route('/mailgun', methods=['POST'])
def mailgun_webhook():
    """
    Mailgun inbound email webhook
    Creates ticket from incoming email
    """
    # Check feature flag
    if not FeatureFlags.is_enabled(FeatureFlag.EMAIL_INGESTION):
        logger.warning("Email ingestion disabled - webhook ignored")
        return jsonify({'message': 'Feature disabled'}), 200
    
    try:
        # Extract email data from Mailgun payload
        sender = request.form.get('sender', '')
        from_name = request.form.get('from', '').split('<')[0].strip()
        subject = request.form.get('subject', 'No Subject')
        body_plain = request.form.get('body-plain', '')
        body_html = request.form.get('body-html', '')
        
        # Use plain text body, fallback to HTML if needed
        description = body_plain if body_plain else body_html
        
        if not sender or not description:
            logger.error("Invalid email payload - missing sender or body")
            return jsonify({'error': 'Invalid payload'}), 400
        
        # Create ticket using service layer
        # AI assistant will be enabled based on feature flag
        ticket = ticket_service.create_ticket(
            subject=subject,
            description=description,
            customer_email=sender,
            customer_name=from_name if from_name else None,
            priority='medium',
            status='open'
        )
        
        logger.info(f"Created ticket {ticket.id} from email: {sender}")
        
        return jsonify({
            'success': True,
            'ticket_id': ticket.id,
            'message': 'Ticket created'
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing inbound email: {str(e)}")
        return jsonify({'error': 'Failed to process email'}), 500