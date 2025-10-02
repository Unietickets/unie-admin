from flask import Blueprint, render_template, session
from routes.auth import is_authenticated
stats_bp = Blueprint("stats", __name__)


@stats_bp.route('/admin/stats')
def stats():
    if is_authenticated():
        return render_template('admin/stats/stats.html', user_active=dict(session))
    return render_template('403.html')