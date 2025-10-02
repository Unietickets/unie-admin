from flask import Blueprint, render_template, session
from routes.auth import is_authenticated

teams_bp = Blueprint("teams_bp", __name__)


@teams_bp.route('/admin/team')
def team():
    if is_authenticated():
        return render_template('admin/stats/stats.html', user_active=dict(session))
    return render_template('403.html')