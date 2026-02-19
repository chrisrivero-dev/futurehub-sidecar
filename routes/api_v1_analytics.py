"""
routes/api_v1_analytics.py
Flask Blueprint for analytics endpoints.
Phase 2: Historical aggregation only.
"""

from flask import Blueprint, jsonify
from datetime import datetime

from services.memory_service import get_weekly_ticket_rows
from services.analysis_service import aggregate_weekly_stats

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.route("/weekly", methods=["GET"])
def weekly_analytics():
    """
    GET /api/v1/analytics/weekly
    Returns aggregated analytics for the last 7 days.
    Always returns 200 — zeroed structure if no data.
    """
    rows = get_weekly_ticket_rows(days=7)
    stats = aggregate_weekly_stats(rows)

    return jsonify({
        "success": True,
        "period": "last_7_days",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        **stats,
    }), 200
