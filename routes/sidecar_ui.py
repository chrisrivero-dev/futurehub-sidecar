from flask import Blueprint, render_template

sidecar_ui_bp = Blueprint(
    'sidecar_ui',
    __name__,
    url_prefix='/sidecar'
)

@sidecar_ui_bp.route('/', methods=['GET'])
def sidecar_console():
    """
    Visual console for AI Sidecar
    """
    return render_template('ai_sidecar.html')

