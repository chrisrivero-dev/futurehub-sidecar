from flask import Blueprint, render_template

sidecar_ui_bp = Blueprint(
    'sidecar_ui',
    __name__,
    url_prefix='/sidecar'
)

from flask import render_template
from app import _build_id  # or move _build_id into a shared util

@sidecar_ui_bp.route("/sidecar/")
def sidecar():
    return render_template(
        "ai_sidecar.html",
        build_id=_build_id(),
    )
