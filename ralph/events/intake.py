from ralph.models import db, Event


def ingest_event(payload: dict) -> int:
    """
    Append-only event ingestion.

    Ralph observes what already happened.
    This function MUST NOT:
    - modify existing events
    - write back to any external system
    - trigger analytics execution
    """

    event = Event(
        event_type=payload["event_type"],
        source_system=payload["source_system"],
        intent=payload["intent"],
        confidence_score=float(payload["confidence_score"]),
        outcome=payload["outcome"],
    )

    db.session.add(event)
    db.session.commit()

    return event.id
