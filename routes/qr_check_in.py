from flask import Blueprint, session, render_template

from routes.auth import is_authenticated

qr_check_in_bp = Blueprint("qr_check_in", __name__)


@qr_check_in_bp.route('/admin/qr_check_in', methods=['GET'])
def admin_qr_check_in():
    if is_authenticated():
        return render_template('admin/qr_scanner/qr_scanner.html', user_active=dict(session))
    else:
        return render_template('403.html')
