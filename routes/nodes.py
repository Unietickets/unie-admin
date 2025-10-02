import secrets
import string
import uuid

from flask import Blueprint, redirect, url_for, request, render_template, session
from werkzeug.security import generate_password_hash

import mailer
from extensions import db
from models import AdminUsers, Nodes
from routes.auth import is_authenticated

nodes_bp = Blueprint("nodes", __name__)


def generate_password_user(length: int = 8,
                           use_lower: bool = True,
                           use_upper: bool = True,
                           use_digits: bool = True,
                           use_symbols: bool = True) -> str:
    """Генератор паролей.
    length      – длина пароля
    use_lower   – использовать строчные буквы
    use_upper   – использовать заглавные буквы
    use_digits  – использовать цифры
    use_symbols – использовать спецсимволы
    """
    alphabet = ""
    if use_lower:
        alphabet += string.ascii_lowercase
    if use_upper:
        alphabet += string.ascii_uppercase
    if use_digits:
        alphabet += string.digits
    if use_symbols:
        alphabet += "!@#$%^&*_-+=?."

    if not alphabet:
        raise ValueError("Нужно выбрать хотя бы один набор символов")

    # гарантируем, что хотя бы по одному символу из каждого выбранного набора
    required = []
    if use_lower:
        required.append(secrets.choice(string.ascii_lowercase))
    if use_upper:
        required.append(secrets.choice(string.ascii_uppercase))
    if use_digits:
        required.append(secrets.choice(string.digits))
    if use_symbols:
        required.append(secrets.choice("!@#$%^&*_-+=?."))

    # остальное добиваем случайными
    while len(required) < length:
        required.append(secrets.choice(alphabet))

    # перемешиваем список
    secrets.SystemRandom().shuffle(required)
    return "".join(required)


def create_user_node(email, role, context_type, node_id):
    if node_id == '':
        node_id = str(uuid.uuid4())
    password_user = generate_password_user(8)
    mailer.send_mail('Welcome to UnieAdmin', 'exchangebots@gmail.com', [email], f'''
                            Your login: {email}
                            Your password: {password_user}
                            If you did not make this request then simply ignore this email and no changes will be made.
                            ''')
    user = AdminUsers(email=email, password_hash=generate_password_hash(password_user),
                      role=role, user_hash='',
                      node_id=node_id)
    db.session.add(user)
    db.session.commit()
    return user


@nodes_bp.route('/admin/nodes/create', methods=['POST'])
def create_nodes():
    if is_authenticated():
        node_gen = str(uuid.uuid4())
        node = Nodes(name=request.form['org_name'], slug=request.form['slug'], commission=request.form['commission'],
                     id=node_gen, main_organizer_id=session['user_id'])
        db.session.add(node)
        db.session.commit()
        create_user_node(request.form['organizer_email'], request.form['role'], request.form['context_type'], node_gen)
        return redirect(url_for('client.admin_users'))
    return render_template('403.html')

@nodes_bp.route('/admin/user_admin/create', methods=['POST'])
def create_user_admin():
    if is_authenticated():
        create_user_node(request.form['email'], request.form['role'], request.form['context_type'], request.form['node_id'])
        return redirect(url_for('admin_users_registrator.users_admin'))
    return render_template('403.html')