"""
routes/webhooks.py
Freshdesk lifecycle webhook receiver.
Handles: reply_sent, customer_replied, status_changed.
All DB writes are non-blocking (failures swallowed + logged).
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from time import perf_counter

from flask import Blueprint, jsonify, request

from db import SessionLocal, safe_commit
from models import (
    DraftEvent,
    TicketReply,
    TicketStatusChange,
    get_or_create_ticket,
)

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/v1/webhooks")

WEBHOOK_SECRET = os.getenv("FRESHDESK_WEBHOOK_SECRET", "")

# ── Auth ──────────────────────────────────────────────────────


def _verify_secret(req):
    """Compare shared secret from header. Returns True if valid."""
    if not WEBHOOK_SECRET:
        return True  # no secret configured — allow (dev mode)
    token = req.headers.get("X-Freshdesk-Webhook-Secret", "")
    return hmac.compare_digest(token, WEBHOOK_SECRET)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Helpers ───────────────────────────────────────────────────


def _find_recent_draft(session, ticket_id: int, before: datetime | None = None):
    """Return the most recent DraftEvent for this ticket within the last 24h."""
    cutoff = (before or datetime.now(timezone.utc)) - timedelta(hours=24)
    return (
        session.query(DraftEvent)
        .filter(
            DraftEvent.ticket_id == ticket_id,
            DraftEvent.created_at >= cutoff,
        )
        .order_by(DraftEvent.created_at.desc())
        .first()
    )


# ── Endpoint ──────────────────────────────────────────────────


@webhooks_bp.route("/freshdesk", methods=["POST"])
def freshdesk_webhook():
    """
    POST /api/v1/webhooks/freshdesk
    """

    if not _verify_secret(request):
        return jsonify({"error": "unauthorized"}), 401

    import json

    raw_body = request.get_data(as_text=True) or ""

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}

    # Handle JSON sent as text/plain
    if not body and raw_body.strip().startswith("{"):
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

    # Handle form encoded payloads
    if not body and request.form:
        body = request.form.to_dict(flat=True)

    event_type = body.get("event_type") or body.get("event") or body.get("type")

    fd_ticket_id = (
        body.get("freshdesk_ticket_id")
        or body.get("ticket_id")
        or body.get("ticketId")
        or body.get("ticket")
    )

    fd_domain = (
        body.get("freshdesk_domain")
        or body.get("domain")
        or body.get("freshdeskDomain")
    )

    data = body.get("data") or {}

    if isinstance(data, str) and data.strip().startswith("{"):
        try:
            data = json.loads(data)
        except Exception:
            data = {}

    # IMPORTANT: swallow malformed webhook instead of 400
    if not event_type or not fd_ticket_id or not fd_domain:
        logger.warning(
            "Webhook missing required fields. content_type=%s raw=%r parsed=%r",
            request.content_type,
            raw_body[:500],
            body,
        )
        return jsonify({"ok": True, "swallowed_error": True}), 200

    # ---- YOUR EXISTING LOGIC CONTINUES BELOW ----

    session = None
    try:
        session = SessionLocal()
        t0 = perf_counter()

        t1 = perf_counter()
        ticket = get_or_create_ticket(session, int(fd_ticket_id), fd_domain)
        logger.info("webhook:get_or_create_ticket ms=%d", int((perf_counter() - t1) * 1000))

        if event_type == "reply_sent":
            result = _handle_reply_sent(session, ticket, data)
        elif event_type == "customer_replied":
            result = _handle_customer_replied(session, ticket, data)
        elif event_type == "status_changed":
            result = _handle_status_changed(session, ticket, data)
        else:
            return jsonify({"error": f"unknown event_type: {event_type}"}), 400

        t2 = perf_counter()
        safe_commit(session)
        logger.info("webhook:safe_commit ms=%d", int((perf_counter() - t2) * 1000))

        logger.info("webhook:total ms=%d", int((perf_counter() - t0) * 1000))
        return jsonify({"ok": True, **result}), 200

    except Exception as e:
        try:
            if session is not None:
                session.rollback()
        except Exception:
            pass

        logger.error("Webhook processing failed (non-fatal): %s", e, exc_info=True)
        return jsonify({"ok": True, "swallowed_error": True}), 200

    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass


# ── Handlers ──────────────────────────────────────────────────


def _handle_reply_sent(session, ticket, data):
    """
    Agent outbound reply was sent from Freshdesk.
    Compare sent body hash against the most recent AI draft hash.
    """
    conv_id = data.get("conversation_id")
    sent_body = data.get("body") or ""

    if not conv_id:
        return {"skipped": "missing conversation_id"}

    # Idempotency: check if already processed
    existing = session.query(TicketReply).filter_by(freshdesk_conversation_id=int(conv_id)).first()
    if existing:
        return {"duplicate": True}

    sent_hash = _sha256(sent_body) if sent_body else None
    sent_len = len(sent_body) if sent_body else 0

    # Link to most recent DraftEvent for this ticket
    draft = _find_recent_draft(session, ticket.id)
    draft_event_id = draft.id if draft else None

    # Override detection: compare hashes only when both exist
    edited = None
    if draft and draft.draft_hash and sent_hash:
        edited = (draft.draft_hash != sent_hash)

    session.add(
        TicketReply(
            ticket_id=ticket.id,
            draft_event_id=draft_event_id,
            direction="outbound",
            freshdesk_conversation_id=int(conv_id),
            body_hash=sent_hash,
            body_length=sent_len,
            edited=edited,
        )
    )
    return {"direction": "outbound", "edited": edited, "draft_linked": draft_event_id is not None}


def _handle_customer_replied(session, ticket, data):
    """
    Inbound customer reply on a ticket.
    Stored as-is. Analytics query determines if it constitutes a follow-up.
    """
    conv_id = data.get("conversation_id")
    body = data.get("body") or ""

    if not conv_id:
        return {"skipped": "missing conversation_id"}

    existing = session.query(TicketReply).filter_by(freshdesk_conversation_id=int(conv_id)).first()
    if existing:
        return {"duplicate": True}

    session.add(
        TicketReply(
            ticket_id=ticket.id,
            draft_event_id=None,
            direction="inbound",
            freshdesk_conversation_id=int(conv_id),
            body_hash=_sha256(body) if body else None,
            body_length=len(body) if body else 0,
            edited=None,
        )
    )
    return {"direction": "inbound"}


def _handle_status_changed(session, ticket, data):
    """
    Ticket status transition.
    Stored as-is. Analytics query determines if it constitutes a reopen.
    """
    old_status = (data.get("old_status") or "").lower()
    new_status = (data.get("new_status") or "").lower()
    updated_at_str = data.get("updated_at")

    if not old_status or not new_status:
        return {"skipped": "missing old_status or new_status"}

    if updated_at_str:
        try:
            fd_updated = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            fd_updated = datetime.now(timezone.utc)
    else:
        fd_updated = datetime.now(timezone.utc)

    session.add(
        TicketStatusChange(
            ticket_id=ticket.id,
            old_status=old_status,
            new_status=new_status,
            freshdesk_updated_at=fd_updated,
        )
    )
    return {"old_status": old_status, "new_status": new_status}