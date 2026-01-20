from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# SQLAlchemy instance (initialized in app.py)
db = SQLAlchemy()


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(64), nullable=False)
    source_system = db.Column(db.String(32), nullable=False)
    intent = db.Column(db.String(64), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    outcome = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ConfidenceCalibration(db.Model):
    __tablename__ = "confidence_calibrations"

    id = db.Column(db.Integer, primary_key=True)
    intent = db.Column(db.String(64), nullable=False)
    recommended_threshold = db.Column(db.Float, nullable=False)
    success_rate = db.Column(db.Float, nullable=False)
    observation_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
