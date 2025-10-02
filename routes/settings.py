from flask import Blueprint, render_template, session
from routes.auth import is_authenticated
settings_bp = Blueprint("settings_bp", __name__)


@settings_bp.route('/admin/settings')
def settings():
    if is_authenticated():
        return render_template('admin/stats/stats.html', user_active=dict(session))
    return render_template('403.html')