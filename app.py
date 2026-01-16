"""
FutureHub AI Sidecar
Application bootstrap
"""

from flask import Flask

# -------------------------
# Create Flask app FIRST
# -------------------------
app = Flask(__name__)
from flask import redirect, url_for

@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("tickets.ticket_list"))


# -------------------------
# Blueprint imports
# -------------------------
from routes.api_tickets import api_tickets_bp
from routes.inbound_email import inbound_email_bp
from routes.tickets import tickets_bp
from routes.ai_draft import ai_draft_bp
from routes.sidecar_ui import sidecar_ui_bp



# -------------------------
# Blueprint registration
# -------------------------
app.register_blueprint(api_tickets_bp)
app.register_blueprint(inbound_email_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(ai_draft_bp)
app.register_blueprint(sidecar_ui_bp)



# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
