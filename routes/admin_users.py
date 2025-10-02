import math
from flask import url_for, redirect, Blueprint, request, session, render_template
from routes.auth import is_authenticated
from models import Nodes,AdminUsers
from extensions import db

admin_users_registrator_bp = Blueprint("admin_users_registrator", __name__)

@admin_users_registrator_bp.route('/')
def hello_world():
    return redirect(url_for('auth.admin_login'))

@admin_users_registrator_bp.route('/admin/users_admin', methods=['GET'])
def users_admin():
    if is_authenticated():
        page = int(request.args.get('page', 1))
        per_page = 10
        if session['context_type'] == 'root':
            nodes = []
            nodes_info = db.session.query(Nodes).all()
            for node in nodes_info:
                nodes.append({'node_name': node.name, 'node_id': node.id})
            base_query = db.session.query(AdminUsers).filter(AdminUsers.email != session['email_user'])
            users_info = (
                db.session.query(AdminUsers)
                .order_by(AdminUsers.id)
                .filter(AdminUsers.email != session['email_user'])
                .all()
            )
            template_page = 'admin/users/users_admin.html'
        else:
            nodes = session['node_id']
            base_query = db.session.query(AdminUsers).filter(AdminUsers.node_id == session['node_id'],AdminUsers.email != session['email_user'])
            users_info = (
                db.session.query(AdminUsers)
                .order_by(AdminUsers.id)
                .filter(AdminUsers.node_id == session['node_id'],AdminUsers.email != session['email_user'])
                .all()
            )
            template_page = 'admin/users/users_admin.html'
        q = request.args.get('q', '').strip()
        if q:
            search = f"%{q.lower()}%"
            query = base_query.filter(
                db.or_(
                    db.func.lower(AdminUsers.email).like(search),
                    db.cast(AdminUsers.id, db.String).like(f"%{q}%")
                )
            )
            found = query.all()
            if not found:
                users_info = []
            else:
                users_info = found
        total = len(users_info)
        users_info = users_info[(page - 1) * per_page: page * per_page]  # Только текущая страница
        total_pages = math.ceil(total / per_page)
        return render_template(template_page,q=q, total_pages=total_pages, page=page, per_page=per_page, user_active=dict(session), users_info=users_info,nodes=nodes)
    else:
        return render_template('403.html')


@admin_users_registrator_bp.route('/admin/admin_users/edit_status', methods=['GET'])
def edit_status_admin_users():
    if is_authenticated():
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        user = db.session.get(AdminUsers, user_id)
        if status == 'true':
            user.status = 'Active'
        else:
            user.status = 'Banned'
        db.session.commit()
        return redirect(url_for('admin_users_registrator.users_admin'))
    return render_template('403.html')