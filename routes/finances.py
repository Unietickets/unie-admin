from flask import Blueprint, render_template, session
from routes.auth import is_authenticated
finances_bp = Blueprint("finances_bp", __name__)


@finances_bp.route('/admin/finance')
def finance():
    if is_authenticated():
        return render_template('admin/stats/stats.html', user_active=dict(session))
    return render_template('403.html')