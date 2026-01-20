from flask import Flask

from ralph.config import Config
from ralph.models import db
from ralph.events.routes import events_bp
from ralph.api.insights import insights_bp



def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(events_bp, url_prefix="/events")
    app.register_blueprint(insights_bp, url_prefix="/insights")

    # Health check (for Railway / local sanity)
    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok", "service": "ralph"}, 200

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
