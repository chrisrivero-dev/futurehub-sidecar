from flask import Blueprint, request, jsonify
from ralph.events.intake import ingest_event

# Blueprint definition (THIS is what app.py imports)
events_bp = Blueprint("events", __name__)

@events_bp.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(force=True)

    required_fields = {
        "event_type",
        "source_system",
        "intent",
        "confidence_score",
        "outcome",
    }

    if not required_fields.issubset(data.keys()):
        return jsonify({"error": "missing required fields"}), 400

    event_id = ingest_event(data)

    return jsonify({
        "status": "accepted",
        "event_id": event_id
    }), 201
