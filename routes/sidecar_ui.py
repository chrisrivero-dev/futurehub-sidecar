from flask import Blueprint, render_template
from app import _build_id  # ✅ import at top-level (important)

sidecar_ui_bp = Blueprint(
    "sidecar_ui",
    __name__,
    url_prefix="/sidecar",
)

@sidecar_ui_bp.route("/", methods=["GET"])
def sidecar():
    return render_template(
        "ai_sidecar.html",
        build_id=_build_id(),
    )
