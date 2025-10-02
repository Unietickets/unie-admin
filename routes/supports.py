from flask import Blueprint, render_template, session
from routes.auth import is_authenticated

supports_bp = Blueprint("support", __name__)


@supports_bp.route('/admin/support')
def support():
    if is_authenticated():
        return render_template('admin/stats/stats.html', user_active=dict(session))
    return render_template('403.html')