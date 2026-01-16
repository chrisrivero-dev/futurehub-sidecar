"""
API routes for ticket operations
Day 2–6: CRUD + Sidecar + Auto-send advisory
"""

from flask import Blueprint, jsonify, request
from models import db, Ticket, Reply
from utils.sidecar_storage import get_sidecar_status
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

api_tickets_bp = Blueprint(
    "api_tickets",
    __name__,
    url_prefix="/api/tickets"
)

# -------------------------------------------------------------------
# Tickets list
# -------------------------------------------------------------------

@api_tickets_bp.route("", methods=["GET"])
def get_tickets():
    """Fetch ticket list with optional filters"""
    try:
        status = request.args.get("status")
        priority = request.args.get("priority")

        query = Ticket.query
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)

        tickets = query.order_by(Ticket.created_at.desc()).all()

        return jsonify({
            "tickets": [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "priority": t.priority,
                    "customer_email": t.customer_email,
                    "created_at": t.created_at.isoformat(),
                    "sidecar_status": t.sidecar_status or "idle",
                    "auto_send_eligible": t.auto_send_eligible or False
                }
                for t in tickets
            ]
        })
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return jsonify({"error": "Failed to fetch tickets"}), 500


# -------------------------------------------------------------------
# Single ticket
# -------------------------------------------------------------------

@api_tickets_bp.route("/<int:ticket_id>", methods=["GET"])
def get_ticket(ticket_id):
    """Fetch single ticket with details"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)

        return jsonify({
            "id": ticket.id,
            "subject": ticket.subject,
            "status": ticket.status,
            "priority": ticket.priority,
            "customer_email": ticket.customer_email,
            "customer_name": ticket.customer_name,
            "description": ticket.description,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "ai_assistant_enabled": ticket.ai_assistant_enabled,
            "sidecar_status": ticket.sidecar_status or "idle",
            "auto_send_eligible": ticket.auto_send_eligible or False,
            "auto_send_reason": ticket.auto_send_reason,
            "auto_send_evaluated_at": (
                ticket.auto_send_evaluated_at.isoformat()
                if ticket.auto_send_evaluated_at else None
            )
        })
    except Exception as e:
        logger.error(f"Error fetching ticket {ticket_id}: {e}")
        return jsonify({"error": "Failed to fetch ticket"}), 500


# -------------------------------------------------------------------
# Replies
# -------------------------------------------------------------------

@api_tickets_bp.route("/<int:ticket_id>/reply", methods=["POST"])
def send_reply(ticket_id):
    """Send reply to ticket"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "Message required"}), 400

        reply = Reply(
            ticket_id=ticket_id,
            author_name=data.get("author_name", "Agent"),
            author_email=data.get("author_email", "support@futurebit.io"),
            message=data["message"],
            created_at=datetime.utcnow()
        )

        db.session.add(reply)
        ticket.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "success": True,
            "reply_id": reply.id,
            "message": "Reply sent successfully"
        })

    except Exception as e:
        logger.error(f"Error sending reply for ticket {ticket_id}: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to send reply"}), 500


# -------------------------------------------------------------------
# Ticket status
# -------------------------------------------------------------------

@api_tickets_bp.route("/<int:ticket_id>/status", methods=["PATCH"])
def update_status(ticket_id):
    """Update ticket status"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)
        data = request.get_json()

        if not data or "status" not in data:
            return jsonify({"error": "Status required"}), 400

        valid_statuses = {"open", "pending", "resolved", "closed"}
        if data["status"] not in valid_statuses:
            return jsonify({"error": "Invalid status"}), 400

        ticket.status = data["status"]
        ticket.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            "success": True,
            "status": ticket.status
        })

    except Exception as e:
        logger.error(f"Error updating status for ticket {ticket_id}: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to update status"}), 500


# -------------------------------------------------------------------
# Sidecar status
# -------------------------------------------------------------------

@api_tickets_bp.route("/<int:ticket_id>/sidecar/status", methods=["GET"])
def get_ticket_sidecar_status(ticket_id):
    """Get sidecar status for ticket"""
    try:
        status = get_sidecar_status(ticket_id)
        if status is None:
            return jsonify({"error": "Ticket not found"}), 404
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error fetching sidecar status for ticket {ticket_id}: {e}")
        return jsonify({"error": "Failed to fetch sidecar status"}), 500


# -------------------------------------------------------------------
# Sidecar analysis (Day 4 mock)
# -------------------------------------------------------------------

@api_tickets_bp.route("/<int:ticket_id>/analysis", methods=["GET"])
def get_ticket_analysis(ticket_id):
    """Return mock AI analysis for UI rendering"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)

        if not ticket.ai_assistant_enabled:
            return jsonify({"error": "AI assistant not enabled"}), 403

        if ticket.sidecar_status != "completed":
            return jsonify({
                "status": ticket.sidecar_status,
                "analysis": None
            })

        return jsonify({
            "status": "completed",
            "analysis": {
                "intent": "shipping_status",
                "confidence": 0.92,
                "analysis": {
                    "summary": "Customer asking about order delivery status",
                    "sentiment": "neutral",
                    "urgency": "medium"
                },
                "draft": (
                    "Thank you for contacting us about your order.\n\n"
                    "Please provide your order number so I can check the status.\n\n"
                    "FutureBit Support"
                ),
                "suggestions": []
            }
        })

    except Exception as e:
        logger.error(f"Error fetching analysis for ticket {ticket_id}: {e}")
        return jsonify({"error": "Failed to fetch analysis"}), 500


# -------------------------------------------------------------------
# Auto-send eligibility (Day 6 advisory only)
# -------------------------------------------------------------------

@api_tickets_bp.route("/<int:ticket_id>/auto-send-eligibility", methods=["GET"])
def get_auto_send_eligibility(ticket_id):
    """Return auto-send eligibility (advisory only)"""
    try:
        ticket = Ticket.query.get_or_404(ticket_id)

        return jsonify({
            "ticket_id": ticket.id,
            "eligible": ticket.auto_send_eligible or False,
            "reason": ticket.auto_send_reason,
            "evaluated_at": (
                ticket.auto_send_evaluated_at.isoformat()
                if ticket.auto_send_evaluated_at else None
            ),
            "sidecar_status": ticket.sidecar_status,
            "note": "Eligibility evaluation only — auto-send not enabled"
        })

    except Exception as e:
        logger.error(f"Error fetching auto-send eligibility for ticket {ticket_id}: {e}")
        return jsonify({"error": "Failed to fetch eligibility"}), 500
