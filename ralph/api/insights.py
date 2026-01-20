from flask import Blueprint, jsonify
from ralph.models import ConfidenceCalibration

# Blueprint definition (THIS is what app.py imports)
insights_bp = Blueprint("insights", __name__)

@insights_bp.route("/calibrations", methods=["GET"])
def get_calibrations():
    rows = ConfidenceCalibration.query.order_by(
        ConfidenceCalibration.created_at.desc()
    ).all()

    return jsonify([
        {
            "intent": row.intent,
            "recommended_threshold": row.recommended_threshold,
            "success_rate": row.success_rate,
            "observation_count": row.observation_count,
            "actionable": False,
            "requires_approval": True
        }
        for row in rows
    ])
