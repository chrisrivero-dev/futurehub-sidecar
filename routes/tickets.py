# routes/tickets.py
"""
Ticket routes for FutureHub
Web UI routes for ticket management
"""

from flask import Blueprint, request, render_template, flash, redirect, url_for
from services.ticket_service import TicketService
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

# Create Blueprint
tickets_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

# Initialize service
ticket_service = TicketService()


@tickets_bp.route('/create', methods=['GET', 'POST'])
def create_ticket():
    """Create new ticket via web form"""
    if request.method == 'GET':
        return render_template('tickets/create.html')
    
    try:
        # Extract form data
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        customer_email = request.form.get('customer_email', '').strip()
        customer_name = request.form.get('customer_name', '').strip()
        priority = request.form.get('priority', 'medium')
        
        # Validate required fields
        if not subject or not description or not customer_email:
            flash('Subject, description, and customer email are required', 'error')
            return render_template('tickets/create.html'), 400
        
        # Create ticket using service layer
        ticket = ticket_service.create_ticket(
            subject=subject,
            description=description,
            customer_email=customer_email,
            customer_name=customer_name if customer_name else None,
            priority=priority,
            status='open'
        )
        
        flash(f'Ticket #{ticket.id} created successfully', 'success')
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket.id))
        
    except Exception as e:
        logger.error(f"Error creating ticket: {str(e)}")
        flash('Failed to create ticket', 'error')
        return render_template('tickets/create.html'), 500


@tickets_bp.route('/<int:ticket_id>', methods=['GET'])
def ticket_detail(ticket_id):
    ticket = {
        "id": ticket_id,
        "subject": "Test Ticket",
        "customer_email": "test@example.com",
        "created_at": datetime.utcnow(),
        "description": "This is a placeholder ticket.",
        "status": "open",
        "ai_assistant_enabled": True,
    }
    return render_template("tickets/detail.html", ticket=ticket)



@tickets_bp.route('/', methods=['GET'])
def ticket_list():
    """View ticket list page"""
    # TODO: Implement ticket list view
    return render_template('tickets/list.html')