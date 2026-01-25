from flask import Blueprint, render_template
from utils.build import build_id

sidecar_ui_bp = Blueprint(
    "sidecar_ui",
    __name__,
    url_prefix="/sidecar",
)

@sidecar_ui_bp.route("/", methods=["GET"])
def sidecar():
    return render_template(
        "ai_sidecar.html",
        build_id=build_id(),
    )
