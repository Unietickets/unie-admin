import math
from flask import Blueprint, render_template, session, request, redirect, url_for
from sqlalchemy import or_, String, cast
from routes.auth import is_authenticated, generate_pass
from extensions import db
from models import User, UserNode

clients_bp = Blueprint("client", __name__)


@clients_bp.route('/admin/clients', methods=['GET'])
def admin_users():
    if is_authenticated():
        page = int(request.args.get('page', 1))
        per_page = 10
        nid = session['node_id']
        if session['context_type'] == 'root':
            base_query = db.session.query(User)
            users_info = (
                db.session.query(User)
                .order_by(User.id)
                .all()
            )
            template_page = 'admin/users/users.html'
        else:
            base_query = db.session.query(User).filter(UserNode.node_id == nid)
            users_info = (
                db.session.query(User)
                .join(UserNode, UserNode.user_id == User.id)
                .filter(UserNode.node_id == nid)
                .order_by(User.id)
                .all()
            )
            template_page = 'admin/users/users.html'
        q = request.args.get('q', '').strip()
        if q:
            search = f"%{q.lower()}%"
            found = (
                base_query
                .filter(
                    or_(
                        User.name.ilike(search),
                        cast(User.id, String).like(f"%{q}%"),
                        User.email.ilike(search),
                        User.phone_number.ilike(search),
                    )
                )
                .order_by(User.id)
                .distinct(User.id)
                .all()
            )
            if not found:
                users_info = []
            else:
                users_info = found
        total = len(users_info)
        users_info = users_info[(page - 1) * per_page: page * per_page]  # Только текущая страница
        total_pages = math.ceil(total / per_page)
        return render_template(template_page,q=q, total_pages=total_pages, page=page, per_page=per_page, user_active=dict(session), users_info=users_info)
    else:
        return render_template('403.html')


@clients_bp.route('/admin/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if is_authenticated():
        user = db.session.get(User, user_id)
        user.name = request.form['name']
        user.email = request.form['email']
        user.phone_number = request.form['phone']
        user.password = request.form['password'] if "scrypt:" in request.form['password'] else generate_pass(
            request.form['password'])
        user.is_active = True if request.form['is_active'] == 'true' else False
        db.session.commit()
        return redirect(url_for('client.admin_users'))
    else:
        return render_template('403.html')


@clients_bp.route('/admin/users/edit_status', methods=['GET'])
def edit_status():
    if is_authenticated():
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        user = db.session.get(User, user_id)
        if status == 'true':
            user.is_active = 1
        else:
            user.is_active = 0
        db.session.commit()
        return redirect(url_for('client.admin_users'))
    return render_template('403.html')


@clients_bp.route('/admin/users/create', methods=['POST'])
def create_user():
    if is_authenticated():
        user = User(name=request.form['name'], email=request.form['email'],
                    password_hash=generate_pass(request.form['password']),
                    is_active=True if request.form['is_active'] == 'true' else False,
                    phone_number=request.form['phone'])
        db.session.add(user)
        db.session.flush()

        user_node = UserNode(node_id=session['node_id'],user_id=user.id)
        db.session.add(user_node)
        db.session.commit()
        return redirect(url_for('client.admin_users'))
    return render_template('403.html')