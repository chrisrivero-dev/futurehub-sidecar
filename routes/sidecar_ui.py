from flask import Blueprint, render_template
import os

sidecar_ui_bp = Blueprint(
    "sidecar_ui",
    __name__,
    url_prefix="/sidecar",
)

def _build_id() -> str:
    sha = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("GIT_COMMIT_SHA")
        or os.getenv("COMMIT_SHA")
        or ""
    )
    return sha[:8] if sha else "dev"

@sidecar_ui_bp.route("/")
def sidecar():
    return render_template(
        "ai_sidecar.html",
        build_id=_build_id(),
    )
