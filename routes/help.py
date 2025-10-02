from flask import Blueprint, render_template, session
from routes.auth import is_authenticated

help_bp = Blueprint("help_bp", __name__)


@help_bp.route('/admin/help')
def help():
    if is_authenticated():
        return render_template('admin/stats/stats.html', user_active=dict(session))
    return render_template('403.html')