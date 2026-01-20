from sqlalchemy import func, case
from ralph.models import db, Event, ConfidenceCalibration


def run_confidence_calibration():
    """
    Analyze past events and recommend confidence thresholds per intent.

    This function:
    - Reads historical events
    - Computes success rates
    - Writes advisory-only calibration records
    - NEVER modifies any external system
    """

    results = (
        db.session.query(
            Event.intent.label("intent"),
            func.count(Event.id).label("count"),
            func.avg(
                case(
                    (Event.outcome == "resolved", 1),
                    else_=0
                )
            ).label("success_rate")
        )
        .group_by(Event.intent)
        .all()
    )

    calibrations = []

    for row in results:
        intent = row.intent
        count = row.count
        success_rate = float(row.success_rate or 0.0)

        # Ignore very small samples
        if count < 1:
            continue

        # Simple, conservative recommendation logic (v1)
        if success_rate >= 0.95:
            recommended = 0.85
        elif success_rate >= 0.85:
            recommended = 0.90
        else:
            recommended = 0.95

        calibration = ConfidenceCalibration(
            intent=intent,
            recommended_threshold=recommended,
            success_rate=round(success_rate, 2),
            observation_count=count
        )

        db.session.add(calibration)
        calibrations.append(calibration)

    db.session.commit()
    return calibrations
