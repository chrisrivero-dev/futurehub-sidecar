"""
routes/api_v1_analytics.py
Flask Blueprint for analytics endpoints.
Phase 2: Historical aggregation + Phase 3: Audit rollups.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime

from services.analytics_service import aggregate_weekly_stats, aggregate_audit_stats

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.route("/weekly", methods=["GET"])
def weekly_analytics():
    """
    GET /api/v1/analytics/weekly
    Returns aggregated analytics for the last 7 days.
    Always returns 200 — zeroed structure if no data.
    """
    stats = aggregate_weekly_stats(days=7)

    return jsonify({
        "success": True,
        "period": "last_7_days",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        **stats,
    }), 200


@analytics_bp.route("/audit", methods=["GET"])
def audit_analytics():
    """
    GET /api/v1/analytics/audit
    Phase 3 — Governance audit metrics for the last 7 days.
    Always returns 200 — zeroed structure if no data.
    """
    stats = aggregate_audit_stats(days=7)

    return jsonify({
        "success": True,
        "period": "last_7_days",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        **stats,
    }), 200


@analytics_bp.route("/rollup", methods=["POST"])
def generate_rollup():
    """
    POST /api/v1/analytics/rollup
    Trigger weekly rollup generation.
    Optional JSON body: {"start_date": "...", "end_date": "..."}
    Returns computed rollup metrics.
    """
    try:
        from audit.rollup import compute_weekly_rollup
    except ImportError:
        return jsonify({"success": False, "error": "Rollup module not available"}), 500

    data = request.get_json(silent=True) or {}
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    metrics = compute_weekly_rollup(start_date=start_date, end_date=end_date)

    return jsonify({
        "success": True,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
    }), 200


@analytics_bp.route("/rollup/latest", methods=["GET"])
def latest_rollup():
    """
    GET /api/v1/analytics/rollup/latest
    Return the most recently generated weekly rollup.
    """
    try:
        from audit.store_sqlite import get_latest_rollup
    except ImportError:
        return jsonify({"success": False, "error": "Rollup module not available"}), 500

    rollup = get_latest_rollup()
    if not rollup:
        return jsonify({
            "success": True,
            "rollup": None,
            "message": "No rollups generated yet.",
        }), 200

    return jsonify({
        "success": True,
        "rollup": rollup,
    }), 200
