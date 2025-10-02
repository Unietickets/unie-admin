from flask import Blueprint, current_app, flash, redirect, url_for, request, render_template
from itsdangerous import Serializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash
from extensions import db
from models import AdminUsers
from routes.auth import is_authenticated
import mailer

password_bp = Blueprint("password_bp", __name__)


def get_reset_password_token(user_email):
    expires_in = 3600  # 1 hour
    s = Serializer(current_app.config['SECRET_KEY'], str(expires_in))
    return s.dumps({'email': user_email})

def verify_reset_password_token(token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, salt='reset-password')
    except SignatureExpired:
        # Token has expired
        flash('The password reset link has expired. Please request a new one.')
        return redirect(url_for('password_bp.forgot_password'))
    except BadSignature:
        # Token is invalid
        flash('The password reset link is invalid. Please request a new one.')
        return redirect(url_for('password_bp.forgot_password'))
    return data.get('user_id')

def confirm_reset_password_token(token):
    s = Serializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except SignatureExpired:
        # Signature expired. Token is no longer valid
        return None
    except BadSignature:
        # Invalid signature. Token is invalid
        return None
    return data.get('email')

@password_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if is_authenticated():
        return redirect(url_for('stats.stats'))
    if request.method == 'POST':
        email = request.form['email']
        user = AdminUsers.query.filter(AdminUsers.email == email).first()
        if user:
            token = get_reset_password_token(email)
            mailer.send_mail('Password Reset Request','exchangebots@gmail.com',[email],f'''To reset your password, visit the following link:
                {url_for('password_bp.reset_password', token=token, _external=True)}
                If you did not make this request then simply ignore this email and no changes will be made.
                ''')
            flash('An email has been sent with instructions to reset your password.', 'info')
            return render_template('forgot_password.html', send_reset_password_url=True)
        else:
            return render_template('forgot_password.html', email_error = True)
    return render_template('forgot_password.html')

@password_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if is_authenticated():
        return redirect(url_for('stats.stats'))
    user = verify_reset_password_token(token)
    if not user:
        flash('Invalid or expired token.', 'warning')
        return redirect(url_for('password_bp.forgot_password'))
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            email = token.split(': "')[1].split('"')[0]
            user = AdminUsers.query.filter(AdminUsers.email == email).first()
            user.password_hash = generate_password_hash(password)
            db.session.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('auth.admin_login'))
    return render_template('reset_password.html', title='Reset Password', token=token)