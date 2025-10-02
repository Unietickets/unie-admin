from flask import Blueprint, session, redirect, url_for, request, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from models import AdminUsers

auth_bp = Blueprint("auth", __name__)

def generate_pass(password):
    password_hash = generate_password_hash(password)
    return password_hash

def is_authenticated():
    return 'user_id' in session

@auth_bp.route('/admin/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.admin_login'))


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_authenticated():
        return redirect(url_for('stats.stats'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = AdminUsers.query.filter(AdminUsers.email == email).first()
        if user:
            if check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['node_id'] = user.node_id
                #TODO  context_type автоматом по роли выдавать
                session['email_user'] = email
                session['role'] = user.role
                return redirect(url_for('stats.stats'))
            return render_template('login.html', password_error=True)
        else:
            return render_template('login.html', email_error=True)
    else:
        return render_template('login.html')


