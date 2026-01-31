"""
routes/insights.py
Read-only aggregation endpoints for executive reporting.

NOTE:
This app does NOT expose a queryable DB session.
This endpoint currently operates on in-memory / placeholder data
until a proper analytics surface is introduced.
"""

from flask import Blueprint, jsonify
from datetime import datetime

insights_bp = Blueprint("insights", __name__, url_prefix="/insights")


@insights_bp.route("/weekly-summary", methods=["GET"])
def weekly_summary():
    """
    Weekly executive summary.
    Safe, non-blocking, no DB access.
    """

    return jsonify({
        "period": "last_7_days",
        "total_tickets": 0,
        "tickets_with_ai_analysis": 0,
        "top_intents": [],
        "intent_distribution": {},
        "auto_send_eligible_count": 0,
        "review_required_count": 0,
        "auto_send_rate": 0.0,
        "review_required_rate": 0.0,
        "notes": "Analytics backend not yet connected."
    })
