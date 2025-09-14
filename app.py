import math
import os
import secrets
import shutil
import string
import uuid
from datetime import datetime, date, timedelta
import boto3
from flask import Flask, session, redirect, url_for, request, render_template, current_app, flash, abort
from sqlalchemy import VARCHAR, TEXT, DECIMAL, UUID
from itsdangerous import Serializer, BadSignature, SignatureExpired
from flask_mail import Mail, Message
from sqlalchemy.orm import aliased, joinedload
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import ARRAY
from werkzeug.utils import secure_filename

load_dotenv()

db_host = os.getenv("DATABASE_HOST")
db_user = os.getenv("DATABASE_USER")
db_password = os.getenv("DATABASE_PASSWORD")
db_name = os.getenv("DATABASE_NAME")
db_port = os.getenv("DATABASE_PORT")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
db = SQLAlchemy(app)

app.config['SECRET_KEY'] = app.secret_key
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'exchangebots@gmail.com'
app.config['MAIL_PASSWORD'] = 'brhgvxncraffbceq'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['SECURITY_PASSWORD_SALT'] = 'brhgvxncraffbceq'

mail = Mail(app)

s3 = boto3.client(
    "s3",
    aws_access_key_id="access-key",
    aws_secret_access_key="secret-key",
    region_name="region"
)


class User(db.Model):
    __tablename__ = 'User'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    email = db.Column(VARCHAR(255), unique=True, nullable=True)
    password = db.Column(VARCHAR(255), nullable=False)
    phone_number = db.Column(VARCHAR(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    reset_token = db.Column(db.String, nullable=True)
    reset_token_exp = db.Column(db.DateTime, nullable=True)
    verification_code = db.Column(db.String, nullable=True)
    verification_code_exp = db.Column(db.DateTime, nullable=True)
    node_id = db.Column(db.String(36), unique=True)

    transactions = db.relationship('Transaction', backref='user', cascade="all, delete")
    tickets = db.relationship('Ticket', backref='user', cascade="all, delete")
    deals_as_buyer = db.relationship('Deal', backref='buyer', foreign_keys='Deal.buyer_id', cascade="all, delete")
    deals_as_seller = db.relationship('Deal', backref='seller', foreign_keys='Deal.seller_id', cascade="all, delete")
    recommended_events = db.relationship('RecommendedEvent', backref='user', cascade="all, delete")
    user_balances = db.relationship('UserBalance', backref='user', cascade="all, delete")

class Genre(db.Model):
    __tablename__ = 'Genre'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)


class Event(db.Model):
    __tablename__ = 'Event'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)
    status = db.Column(db.Enum('draft', 'upcoming', 'completed', 'cancelled', name='eventstatus'), default='draft')
    genre = db.Column(ARRAY(db.String), default=[])
    tickets_available = db.Column(db.Integer, default=0)
    tickets_sold = db.Column(db.Integer, default=0)
    event_date = db.Column(db.DateTime, nullable=False)
    event_date_end = db.Column(db.DateTime, nullable=False)
    location = db.Column(VARCHAR(255), nullable=True)
    location_address = db.Column(VARCHAR(255), nullable=True)
    city = db.Column(VARCHAR(255), nullable=True)
    description = db.Column(TEXT, nullable=True)
    last_edit = db.Column(db.DateTime, nullable=False)
    price_tickets = db.Column(DECIMAL(10, 2), nullable=False)
    photos = db.relationship('EventPhoto', backref='event', cascade="all, delete")
    tickets = db.relationship('Ticket', backref='event', cascade="all, delete")
    deals = db.relationship('Deal', backref='event', cascade="all, delete")
    recommendations = db.relationship('RecommendedEvent', backref='event', cascade="all, delete")
    node_id = db.Column(
        db.String(36),
        db.ForeignKey('Nodes.node_id', ondelete='CASCADE'),
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )


class Transaction(db.Model):
    __tablename__ = 'Transaction'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=False)
    direction = db.Column(db.Enum('deposit', 'withdraw', name='transactiondirection'))
    amount = db.Column(DECIMAL(10, 2), nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('created', 'in_process', 'completed', name='transactionstatus'), default='created')


class Ticket(db.Model):
    __tablename__ = 'Ticket'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=False)
    buyer_id = db.Column(db.Integer, nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id', ondelete='CASCADE'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.Column(VARCHAR(255), nullable=True)
    status = db.Column(db.Enum('available', 'sold', 'reserved','unverified', name='ticketstatus'), default='available')
    is_verified = db.Column(db.Boolean, default=False)
    price = db.Column(DECIMAL(10, 2), nullable=False)
    description = db.Column(db.String, nullable=True)

    deal_ticket = db.relationship('DealTicket', backref='ticket', uselist=False)


class Deal(db.Model):
    __tablename__ = 'Deal'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id', ondelete='CASCADE'))
    buyer_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'))
    seller_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'))
    deal_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('in_progress', 'completed', 'declined', name='dealstatus'), default='in_progress')
    price = db.Column(DECIMAL(10, 2), nullable=False)

    tickets = db.relationship('DealTicket', backref='deal', cascade="all, delete")


class EventPhoto(db.Model):
    __tablename__ = 'EventPhoto'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id', ondelete='CASCADE'))
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('File.id', ondelete='CASCADE'))
    location = db.Column(VARCHAR(100), nullable=False)


class DealTicket(db.Model):
    __tablename__ = 'DealTicket'

    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('Deal.id', ondelete='CASCADE'))
    ticket_id = db.Column(db.Integer, db.ForeignKey('Ticket.id'), unique=True)


class RecommendedEvent(db.Model):
    __tablename__ = 'RecommendedEvent'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('Event.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=True)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('event_id', 'user_id', name='_event_user_uc'),)


class File(db.Model):
    __tablename__ = 'File'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, unique=True, nullable=False)
    originalname = db.Column(db.String, nullable=False)
    createdat = db.Column(db.DateTime, default=datetime.utcnow)
    size = db.Column(db.Integer, nullable=False)

    event_photos = db.relationship('EventPhoto', backref='file', cascade="all, delete")


class UserBalance(db.Model):
    __tablename__ = 'UserBalance'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'))
    active_balance = db.Column(DECIMAL(10, 2), nullable=False)
    pending_balance = db.Column(DECIMAL(10, 2), nullable=False)
    activation_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserAdmin(db.Model):
    __tablename__ = 'user_admin'
    user_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(100))
    user_hash = db.Column(db.String(100))
    context_type = db.Column(db.String(100))
    status = db.Column(db.String(100), default='Active')
    node_id = db.Column(
        db.String(36),
        db.ForeignKey('Nodes.node_id', ondelete='CASCADE'),
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )


class Nodes(db.Model):
    __tablename__ = 'Nodes'
    id = db.Column(db.Integer, primary_key=True)
    organization_name = db.Column(db.String(100))
    slug = db.Column(db.String(100), unique=True)
    commission = db.Column(db.Integer)
    node_id = db.Column(db.String(36))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)




@app.context_processor
def utility_processor():
    def event_image_path(filename):
        absolute_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        if os.path.exists(absolute_path):
            return url_for('static', filename=f'uploads/{filename}')
        else:
            return url_for('static', filename='uploads/default.png')

    return dict(event_image_path=event_image_path)

@app.before_request
def load_current_user():
    if request.endpoint in ('static','admin_login','forgot_password','reset_password',):
        return
    user_id = session.get('user_id')
    if user_id:
        users_info = db.session.get(UserAdmin, user_id)
        if users_info.status == 'Banned':
            session.pop('user_id', None)
            return
        session['role'] = users_info.role
        session['context_type'] = users_info.context_type
        return
    else:
        return render_template('403.html')


@app.route('/')
def hello_world():
    return redirect(url_for('admin_login'))


def is_authenticated():
    return 'user_id' in session


@app.route('/admin/logout')
def logout():
    session.pop('user_id', None)  # Удалить user_id из сессии, если он там есть
    return redirect(url_for('admin_login'))


def generate_pass(password):
    password_hash = generate_password_hash(password)
    return password_hash

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if is_authenticated():
        return redirect(url_for('stats'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = UserAdmin.query.filter(UserAdmin.email == email).first()
        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.user_id
                session['node_id'] = user.node_id
                session['context_type'] = user.context_type
                session['email_user'] = email
                session['role'] = user.role
                return redirect(url_for('stats'))
            return render_template('login.html', password_error=True)
        else:
            return render_template('login.html', email_error=True)
    else:
        return render_template('login.html')

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
        return redirect(url_for('forgot_password'))
    except BadSignature:
        # Token is invalid
        flash('The password reset link is invalid. Please request a new one.')
        return redirect(url_for('forgot_password'))
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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if is_authenticated():
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email']
        user = UserAdmin.query.filter(UserAdmin.email == email).first()
        if user:
            token = get_reset_password_token(email)
            # print("Tokeeeennn -    " + token)
            msg = Message('Password Reset Request',
                          sender='exchangebots@gmail.com',
                          recipients=[email])
            msg.body = f'''To reset your password, visit the following link:
                {url_for('reset_password', token=token, _external=True)}

                If you did not make this request then simply ignore this email and no changes will be made.
                '''
            mail.send(msg)
            flash('An email has been sent with instructions to reset your password.', 'info')
            return render_template('forgot_password.html', send_reset_password_url=True)
        else:
            return render_template('forgot_password.html', email_error = True)
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if is_authenticated():
        return redirect(url_for('index'))
    user = verify_reset_password_token(token)
    # print(user)
    if not user:
        flash('Invalid or expired token.', 'warning')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            email = token.split(': "')[1].split('"')[0]
            user = UserAdmin.query.filter(UserAdmin.email == email).first()
            # Hash the password
            user.password = generate_password_hash(password)
            db.session.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('admin_login'))
    return render_template('reset_password.html', title='Reset Password', token=token)

@app.route('/admin/stats')
def stats():
    if is_authenticated():
        user_active = session['email_user']
        return render_template('admin/stats.html', user_active=dict(session))
    return render_template('403.html')


@app.route('/admin/clients', methods=['GET'])
def admin_users():
    if is_authenticated():
        page = int(request.args.get('page', 1))
        per_page = 12
        if session['context_type'] == 'root':

            users_info = (
                db.session.query(User)
                .order_by(User.id)
                .all()
            )
            template_page = 'admin/users.html'
        else:

            users_info = (
                db.session.query(User)
                .order_by(User.id)
                .filter(User.node_id == session['node_id'])
                .all()
            )
            template_page = 'admin/users.html'
        q = request.args.get('q', '').strip()
        if q:
            base_query = db.session.query(User)
            search = f"%{q.lower()}%"
            query = base_query.filter(
                db.or_(
                    db.func.lower(User.name).like(search),
                    db.cast(User.id, db.String).like(f"%{q}%")
                )
            )
            found = query.filter(User.node_id == session['node_id']).all()
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


@app.route('/admin/users_admin', methods=['GET'])
def users_admin():
    if is_authenticated():
        page = int(request.args.get('page', 1))
        per_page = 12
        if session['context_type'] == 'root':
            nodes = []
            nodes_info = db.session.query(Nodes).all()
            for node in nodes_info:
                nodes.append({'node_name': node.organization_name, 'node_id': node.node_id})
            base_query = db.session.query(UserAdmin).filter(UserAdmin.email != session['email_user'])
            users_info = (
                db.session.query(UserAdmin)
                .order_by(UserAdmin.user_id)
                .filter(UserAdmin.email != session['email_user'])
                .all()
            )
            template_page = 'admin/users_admin.html'
        else:
            nodes = session['node_id']
            base_query = db.session.query(UserAdmin).filter(UserAdmin.node_id == session['node_id'],UserAdmin.email != session['email_user'])
            users_info = (
                db.session.query(UserAdmin)
                .order_by(UserAdmin.user_id)
                .filter(UserAdmin.node_id == session['node_id'],UserAdmin.email != session['email_user'])
                .all()
            )
            template_page = 'admin/users_admin.html'
        q = request.args.get('q', '').strip()
        if q:
            search = f"%{q.lower()}%"
            query = base_query.filter(
                db.or_(
                    db.func.lower(UserAdmin.email).like(search),
                    db.cast(UserAdmin.user_id, db.String).like(f"%{q}%")
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


@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    if is_authenticated():
        print(request.form)
        user = db.session.get(User, user_id)
        user.name = request.form['name']
        user.email = request.form['email']
        user.phone_number = request.form['phone']
        user.password = request.form['password'] if "scrypt:" in request.form['password'] else generate_pass(
            request.form['password'])
        user.is_active = True if request.form['is_active'] == 'true' else False
        db.session.commit()
        return redirect(url_for('admin_users'))
    else:
        return render_template('403.html')

@app.route('/admin/ticket/edit/<int:ticket_id>', methods=['POST'])
def edit_tickets(ticket_id):
    if is_authenticated():
        print(request.form)
        ticket = db.session.get(Ticket, ticket_id)
        event = db.session.get(Event, int(request.form['event_name']))
        old_status = ticket.status
        new_status = request.form['status']

        ticket.user_id = request.form['user_name']
        ticket.event_id = request.form['event_name']
        ticket.price = request.form['cost']
        ticket.status = request.form['status']
        ticket.description = request.form['ticket_desc']
        if old_status != new_status:
            if old_status == 'available':
                event.tickets_available -= 1
            if new_status == 'available':
                event.tickets_available += 1
            if new_status == 'sold':
                event.tickets_sold += 1
            # Защита от отрицательных значений
            if event.tickets_available < 0:
                event.tickets_available = 0
        db.session.commit()
        return redirect(url_for('admin_tickets'))
    else:
        return render_template('403.html')

# @app.route('/admin/event/edit/<int:event_id>', methods=['POST'])
# def edit_event(event_id):
#     if is_authenticated():
#         print(request.form)
#         event = db.session.get(Event, event_id)
#         event.name = request.form['name']
#         event.genre = request.form['genre_id']
#         event.event_date = request.form['event_date']
#         event.event_date_end = request.form['event_end_date']
#         event.location = request.form['location']
#         event.location_address = request.form['location_address']
#         event.city = request.form['city']
#         event.tickets_available = request.form['ticket_quantity']
#         event.description = request.form['description']
#         db.session.commit()
#
#         # Получаем файлы
#         photo_card = request.files.get('photo_card')
#         photo_page = request.files.get('photo_page')
#
#         # Загружаем, если они действительно есть
#         if photo_card and photo_card.filename:
#             file_info = (
#                 db.session.query(EventPhoto)
#                 .filter(EventPhoto.location == 'card')
#                 .filter(EventPhoto.event_id == event_id)
#                 .first()
#             )
#             if file_info:
#                 old_file = file_info.file_id
#                 photo_card_id = upload_file(photo_card, 'media')
#                 file_info.file_id = photo_card_id
#                 db.session.commit()
#                 delete_file('media', old_file)
#             else:
#                 photo_card_id = upload_file(photo_card, 'media')
#                 db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='card'))
#                 db.session.commit()
#         if photo_page and photo_page.filename:
#             file_info = (
#                 db.session.query(EventPhoto)
#                 .filter(EventPhoto.location == 'page')
#                 .filter(EventPhoto.event_id == event_id)
#                 .first()
#             )
#             if file_info:
#                 old_file = file_info.file_id
#                 photo_page_id = upload_file(photo_page, 'media')
#                 file_info.file_id = photo_page_id
#                 db.session.commit()
#                 delete_file('media', old_file)
#             else:
#                 photo_page_id = upload_file(photo_page, 'media')
#                 db.session.add(EventPhoto(event_id=event_id, file_id=photo_page_id, location='page'))
#                 db.session.commit()
#         return redirect(url_for('admin_events'))
#     else:
#         return render_template('403.html')

def format_last_edit(ts):
    now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
    date_str = ""
    if ts.date() == now.date():
        date_str = "today"
    elif ts.date() == (now - timedelta(days=1)).date():
        date_str = "yesterday"
    else:
        date_str = ts.strftime('%d %b %Y')
    time_str = ts.strftime('%H:%M')
    return f"Last edit {date_str} at {time_str}"

@app.route('/admin/event/<int:event_id>', methods=['GET'])
def info_event(event_id):
    if is_authenticated():
        photo_card = aliased(EventPhoto)
        photo_page = aliased(EventPhoto)
        file_card = aliased(File)
        file_page = aliased(File)
        base_query = (
            db.session.query(Event)
            .outerjoin(photo_card, (photo_card.event_id == Event.id) & (photo_card.location == 'card'))
            .outerjoin(file_card, file_card.id == photo_card.file_id)
            .outerjoin(photo_page, (photo_page.event_id == Event.id) & (photo_page.location == 'page'))
            .outerjoin(file_page, file_page.id == photo_page.file_id)
            .add_columns(
                file_card.id.label("card_filename"),
                file_page.id.label("page_filename"),
                file_card.originalname.label("card_ext"),
                file_page.originalname.label("page_ext")
            )
            .filter(Event.id == event_id)
        )
        events = base_query.all()
        events_info = []
        for event_obj, card_filename, page_filename, card_ext, page_ext in events:
            event_obj.card_filename = str(card_filename)
            event_obj.page_filename = str(page_filename)
            event_obj.card_ext = get_extension(card_ext)
            event_obj.page_ext = get_extension(page_ext)
            events_info.append(event_obj)
        event = events_info[0]
        genre_all = db.session.query(Genre).all()
        date_format = (
            f"{event.event_date.strftime('%A, %d %B %Y')}  {event.event_date.strftime('%H:%M')} - {event.event_date_end.strftime('%H:%M')}"
        )
        genre_all_list = []
        for genre in genre_all:
            genre_all_list.append(genre.name)
        last_edit = format_last_edit(event.last_edit)
        node_info = db.session.query(Nodes).filter(Nodes.node_id == session['node_id']).first()
        selling_fees = node_info.commission
        buyer_will_pay = round(float(event.price_tickets) * selling_fees / 100)
        return render_template('admin/event_info.html', event=event, date_format=date_format, genre_all_list=genre_all_list,last_edit=last_edit, selling_fees=selling_fees, buyer_will_pay=buyer_will_pay,user_active=dict(session))
    else:
        return render_template('403.html')


@app.route('/admin/genre/edit/<int:event_id>/<string:genre>/<string:action>', methods=['POST'])
def edit_genre(event_id, genre, action):
    if is_authenticated():
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('info_event', event_id=event_id))
        genres = event.genre or []
        if action == "add":
            if genre == "bulk":
                data = request.get_json()
                genres = [g for g in data.get('genres', [])]
            else:
                if genre not in genres:
                    genres.append(genre)
        elif action == "delete":
            genres = [g for g in genres if g != genre]
        else:
            flash('Unknown action', 'error')
            return redirect(url_for('info_event', event_id=event_id))
        event.genre = genres
        db.session.commit()
        flash('Genre updated', 'success')
        return redirect(url_for('info_event', event_id=event_id))
    else:
        return render_template('403.html')

@app.route('/admin/event/edit/<int:event_id>', methods=['POST'])
def edit_dates_event(event_id):
    if is_authenticated():
        user_active = session['email_user']
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('info_event', event_id=event_id, user_active=dict(session)))
        data = request.get_json()
        event.event_date = data['start_date'] + ' ' + data['start_time']
        event.event_date_end = data['end_date'] + ' ' + data['end_time']
        db.session.commit()
        flash('Dates updated', 'success')
        return redirect(url_for('info_event', event_id=event_id, user_active=dict(session)))
    else:
        return render_template('403.html')

@app.route('/admin/users/edit_status', methods=['GET'])
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
        return redirect(url_for('admin_users'))
    return render_template('403.html')

@app.route('/admin/admin_users/edit_status', methods=['GET'])
def edit_status_admin_users():
    if is_authenticated():
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        user = db.session.get(UserAdmin, user_id)
        if status == 'true':
            user.status = 'Active'
        else:
            user.status = 'Banned'
        db.session.commit()
        return redirect(url_for('users_admin'))
    return render_template('403.html')

@app.route('/admin/tickets/edit_status', methods=['GET'])
def tickets_edit_status():
    if is_authenticated():
        ticket_id = request.args.get('ticket_id')
        status = request.args.get('status')
        ticket = db.session.get(Ticket, ticket_id)
        event = db.session.get(Event, request.args.get('event_id'))
        if status == 'true':
            ticket.is_verified = 1
            event.tickets_available -= 1
        else:
            event.tickets_available += 1
            ticket.status = 'unverified'
        db.session.commit()
        return redirect(url_for('admin_tickets_request'))
    return render_template('403.html')


@app.route('/admin/users/create', methods=['POST'])
def create_user():
    if is_authenticated():
        user = User(name=request.form['name'], email=request.form['email'],
                    password=generate_pass(request.form['password']),
                    is_active=True if request.form['is_active'] == 'true' else False,
                    phone_number=request.form['phone'], node_id=session['node_id'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('admin_users'))
    return render_template('403.html')


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

    msg = Message('Welcome to UnieAdmin',
                  sender='exchangebots@gmail.com',
                  recipients=[email])
    msg.body = f'''Your login: {email}
                            Your password: {password_user}
                            If you did not make this request then simply ignore this email and no changes will be made.
                            '''
    mail.send(msg)
    user = UserAdmin(email=email, password=generate_password_hash(password_user),
                     role=role, user_hash='', context_type=context_type,
                     node_id=node_id, status='Active')
    db.session.add(user)
    db.session.commit()
    return user


@app.route('/admin/nodes/create', methods=['POST'])
def create_nodes():
    if is_authenticated():
        node_gen = str(uuid.uuid4())
        node = Nodes(organization_name=request.form['org_name'],slug=request.form['slug'],commission=request.form['commission'], node_id=node_gen)
        db.session.add(node)
        db.session.commit()
        create_user_node(request.form['organizer_email'], request.form['role'], request.form['context_type'], node_gen)
        return redirect(url_for('admin_users'))
    return render_template('403.html')

@app.route('/admin/user_admin/create', methods=['POST'])
def create_user_admin():
    if is_authenticated():
        print(request.form)
        create_user_node(request.form['email'], request.form['role'], request.form['context_type'], request.form['node_id'])
        return redirect(url_for('users_admin'))
    return render_template('403.html')


def upload_file(file, bucket):
    UPLOAD_DIR = "static/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file)[1]
    file_id = str(uuid.uuid4())
    local_filename = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, local_filename)
    basename = os.path.basename(file)
    shutil.move(file, save_path)
    filename_in_s3 = f"events/{file_id}"
    # Определение реального размера файла
    size = os.path.getsize(save_path)

    # s3.upload_fileobj(
    #     Fileobj=file.stream,
    #     Bucket=bucket,
    #     Key=filename_in_s3,
    #     ExtraArgs={"ContentType": file.mimetype}
    # )

    # Сохраняем в таблицу File
    new_file = File(
        id=file_id,
        bucket=bucket,
        filename=filename_in_s3,
        originalname=basename,
        size=size
    )
    db.session.add(new_file)
    db.session.commit()

    return file_id


def delete_file(bucket, old_file_id):
    #Удаляем старый файл
    old_file = db.session.get(File, old_file_id)
    if old_file:
        try:
            #Логика удаления из С3
            pass
            # s3.delete_object(Bucket=old_file.bucket, Key=old_file.filename)
        except Exception as e:
            print(f"Ошибка удаления файла из S3: {e}")
        db.session.delete(old_file)

    db.session.commit()
    return


def get_extension(filename):
    if filename and '.' in filename:
        return filename.rsplit('.', 1)[1]
    return ''


# @app.route('/admin/events/create', methods=['POST'])
# def create_event():
#     print(request.form)
#     if is_authenticated():
#         event = Event(name=request.form['name'], genre=request.form['genre_id'],
#                       event_date=request.form['event_date'], location=request.form['location'],
#                       description=request.form['description'],event_date_end=request.form['event_end_date'],location_address=request.form['location_address'],city=request.form['city'])
#         db.session.add(event)
#         db.session.commit()
#         event_id = event.id
#
#         # Получаем файлы
#         photo_card = request.files.get('photo_card')
#         photo_page = request.files.get('photo_page')
#
#         # Загружаем, если они действительно есть
#         if photo_card and photo_card.filename:
#             photo_card_id = upload_file(photo_card, 'media')
#             db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='card'))
#
#         if photo_page and photo_page.filename:
#             photo_page_id = upload_file(photo_page, 'media')
#             db.session.add(EventPhoto(event_id=event_id, file_id=photo_page_id, location='page'))
#         db.session.commit()
#         return redirect(url_for('admin_events'))
#     return render_template('403.html')

@app.route('/admin/events/cancel', methods=['GET', 'POST'])
def cancel_event_creation():
    image_filename = session.pop('temp_image', None)  # или другой ключ
    session.pop('event_cover_path', None)
    if image_filename:
        path = os.path.join(app.root_path, 'static', 'tmp', image_filename)
        if os.path.exists(path):
            os.remove(path)
    return redirect(url_for('admin_events'))

@app.route('/admin/events/create', methods=['GET', 'POST'])
def create_event():
    if not is_authenticated():
        return render_template('403.html')
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'tmp')
    if request.method == 'POST':
        if request.form.get('step') == 'step_1':
            session['event_name'] = request.form.get('event_name')
            session['event_desc'] = request.form.get('event_desc')
            file = request.files['event_cover']
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            if file and file.filename:
                file = request.files['event_cover']
                filename = secure_filename(file.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                session['temp_image'] = save_path
                session['event_cover_path'] = filename
            return render_template('admin/events_create_step_2.html', user_active=dict(session))
        elif request.form.get('step') == 'step_2':
            session['start_date'] = request.form.get('start_date')
            session['start_time'] = request.form.get('start_time')
            session['end_date'] = request.form.get('end_date')
            session['end_time'] = request.form.get('end_time')
            session['venue_name'] = request.form.get('venue_name')
            session['venue_city'] = request.form.get('venue_city')
            session['venue_address'] = request.form.get('venue_address')
            return render_template('admin/events_create_step_3.html', user_active=dict(session))
        elif request.form.get('step') == 'step_3':
            try:
                genres_str = request.form.get('genres', '')
                available_quantity_tickets = request.form.get('available_quantity')
                price = request.form.get('price')
                last_updated = datetime.now()
                genres_list = [g.strip() for g in genres_str.split(',') if g.strip()]
                start_dt = f"{session['start_date']} {session['start_time']}"
                end_dt = f"{session['end_date']} {session['end_time']}"
                event = Event(name=session['event_name'], genre=genres_list,tickets_available=available_quantity_tickets,price_tickets=price,
                              event_date=start_dt, location=session['venue_name'],
                              description=session['event_desc'],event_date_end=end_dt,location_address=session['venue_address'],city=session['venue_city'],last_edit=last_updated, node_id=session['node_id'])
                db.session.add(event)
                db.session.commit()
                event_id = event.id


                # photo_card = request.files.get('photo_card')
                # photo_page = request.files.get('photo_page')
                filename = session.get('event_cover_path')
                #TODO Надо проработать фото
                if filename:
                    photo_card_id = upload_file(session['temp_image'], 'media')
                    db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='card'))
                    db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='page'))
                db.session.commit()
            except Exception as e:
                print(e)
                return render_template('admin/events_create_step_3.html', user_active=dict(session), show_modal='error')
            return render_template('admin/events_create_step_3.html', user_active=dict(session), show_modal=True)

    filename = session.get('event_cover_path')
    event_image_url = None
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            event_image_url = '/static/tmp/' + filename
        else:
            session.pop('event_cover_path')

    return render_template('admin/events_create_step_1.html', event_image_url=event_image_url, user_active=dict(session))


@app.route('/admin/tickets/create', methods=['POST'])
def create_ticket():
    if is_authenticated():
        ticket_quantity = int(request.form['ticket_quantity'])
        event = db.session.get(Event, request.form['event_name'])
        for _ in range(ticket_quantity):
            user_id = request.form['user_name']
            ticket = Ticket(user_id=user_id, event_id=request.form['event_name'], status=request.form['status'],
                            is_verified=False, price=request.form['cost'], description=request.form['ticket_desc'])
            db.session.add(ticket)
            if request.form['status'] == 'available':
                event.tickets_available += 1
            elif request.form['status'] in ['sold']:
                if event.tickets_available > 0:
                    event.tickets_sold += 1
                    event.tickets_available -= 1
            elif request.form['status'] in ['reserved']:
                if event.tickets_available > 0:
                    event.tickets_available -= 1
        db.session.commit()
        return redirect(url_for('admin_tickets'))
    return render_template('403.html')

def attach_images_to_events(events):
    event_ids = [e.id for e in events]
    # Получить карточки-фотки одной пачкой
    photo_card = aliased(EventPhoto)
    photo_page = aliased(EventPhoto)
    file_card = aliased(File)
    file_page = aliased(File)

    photos = (
        db.session.query(Event.id,
                         file_card.id.label("card_filename"),
                         file_page.id.label("page_filename"),
                         file_card.originalname.label("card_ext"),
                         file_page.originalname.label("page_ext"))
        .join(photo_card, (photo_card.event_id == Event.id) & (photo_card.location == 'card'))
        .join(file_card, file_card.id == photo_card.file_id)
        .join(photo_page, (photo_page.event_id == Event.id) & (photo_page.location == 'page'))
        .join(file_page, file_page.id == photo_page.file_id)
        .filter(Event.id.in_(event_ids))
        .all()
    )
    # Мапим по id
    photos_by_id = {row.id: row for row in photos}
    for event_obj in events:
        photo = photos_by_id.get(event_obj.id)
        if photo:
            event_obj.card_filename = str(photo.card_filename)
            event_obj.page_filename = str(photo.page_filename)
            event_obj.card_ext = get_extension(photo.card_ext)
            event_obj.page_ext = get_extension(photo.page_ext)
        else:
            event_obj.card_filename = event_obj.page_filename = None
            event_obj.card_ext = event_obj.page_ext = None
    return events


@app.route('/admin/events', methods=['GET', 'POST'])
def admin_events():
    if is_authenticated():
        if request.method == 'GET':
            page = int(request.args.get('page', 1))
            per_page = 8
            photo_card = aliased(EventPhoto)
            photo_page = aliased(EventPhoto)
            file_card = aliased(File)
            file_page = aliased(File)
            tab = request.args.get('tab', 'unpublished')
            q = request.args.get('q', '').strip()
            now = datetime.now()
            if session['context_type'] == 'root':
                base_query = db.session.query(Event)
            else:
                base_query = db.session.query(Event).filter(Event.node_id == session['node_id'])
            if q:
                search = f"%{q.lower()}%"
                query = base_query.filter(
                    db.or_(
                        db.func.lower(Event.name).like(search),
                        db.cast(Event.id, db.String).like(f"%{q}%")
                    )
                )
                found = query.order_by(Event.event_date).all()
                # определяем, к какому табу относятся найденные ивенты
                if not found:
                    found_tab = None
                    events_info = []
                else:
                    # first event in found — определяем по дате и статусу в какой таб попадает
                    event = found[0]
                    if event.status == 'draft':
                        found_tab = 'unpublished'
                    elif event.event_date > now:
                        found_tab = 'upcoming'
                    else:
                        found_tab = 'past'
                    events_info = attach_images_to_events(found)
                unpublished_count = base_query.filter(Event.status == 'draft').count()
                # Пагинация вручную
                total = len(events_info)  # <= Вот это total!
                events_info = events_info[(page - 1) * per_page: page * per_page]  # Только текущая страница
                total_pages = math.ceil(total / per_page)
                return render_template('admin/events.html',
                                       events_info=events_info,
                                       current_tab=found_tab,
                                       unpublished_count=unpublished_count,
                                       q=q, total_pages=total_pages, page=page, per_page=per_page,user_active=dict(session))
            else:
                if session['context_type'] == 'root':
                    base_query = (
                        db.session.query(Event)
                        .outerjoin(photo_card, (photo_card.event_id == Event.id) & (photo_card.location == 'card'))
                        .outerjoin(file_card, file_card.id == photo_card.file_id)
                        .outerjoin(photo_page, (photo_page.event_id == Event.id) & (photo_page.location == 'page'))
                        .outerjoin(file_page, file_page.id == photo_page.file_id)
                        .add_columns(
                            file_card.id.label("card_filename"),
                            file_page.id.label("page_filename"),
                            file_card.originalname.label("card_ext"),
                            file_page.originalname.label("page_ext")
                        )
                    )
                else:
                    base_query = (
                        db.session.query(Event)
                        .filter(Event.node_id == session['node_id'])
                        .outerjoin(photo_card, (photo_card.event_id == Event.id) & (photo_card.location == 'card'))
                        .outerjoin(file_card, file_card.id == photo_card.file_id)
                        .outerjoin(photo_page, (photo_page.event_id == Event.id) & (photo_page.location == 'page'))
                        .outerjoin(file_page, file_page.id == photo_page.file_id)
                        .add_columns(
                            file_card.id.label("card_filename"),
                            file_page.id.label("page_filename"),
                            file_card.originalname.label("card_ext"),
                            file_page.originalname.label("page_ext")
                        )
                    )

                # 2. Фильтрация по табу
                if tab == 'upcoming':
                    base_query = base_query.filter(Event.event_date > now, Event.status != 'draft')
                elif tab == 'past':
                    base_query = base_query.filter(Event.event_date_end < now, Event.status != 'draft')
                elif tab == 'unpublished':
                    base_query = base_query.filter(Event.status == 'draft')

                # 3. Подсчет общего количества событий
                total_events = base_query.count()
                total_pages = (total_events + per_page - 1) // per_page

                # 4. Пагинация
                events = (
                    base_query
                    .order_by(Event.event_date)
                    .limit(per_page)
                    .offset((page - 1) * per_page)
                    .all()
                )

                events_info = []
                for event_obj, card_filename, page_filename, card_ext, page_ext in events:
                    event_obj.card_filename = str(card_filename)
                    event_obj.page_filename = str(page_filename)
                    event_obj.card_ext = get_extension(card_ext)
                    event_obj.page_ext = get_extension(page_ext)
                    events_info.append(event_obj)

                unpublished_count = db.session.query(Event).filter(Event.status == 'draft').count()

                return render_template(
                    'admin/events.html',
                    user_active=dict(session),
                    today=(date.today() + timedelta(days=1)).isoformat(),
                    events_info=events_info,
                    current_tab=tab,
                    unpublished_count=unpublished_count,
                    page=page,
                    total_pages=total_pages
                )
        else:
            if request.form['action'] == 'add':
                event = db.session.query(Event).filter_by(id=request.form['event_id']).first()
                event.status = 'upcoming'
                db.session.commit()
                tab = request.args.get('tab', 'upcoming')
                return redirect(url_for('admin_events', tab=tab))
            elif request.form['action'] == 'delete':
                event = db.session.get(Event, request.form['event_id'])
                db.session.delete(event)
                #TODO добавить удаление файлов
                db.session.commit()
                tab = request.args.get('tab', 'unpublished')
                return redirect(url_for('admin_events', tab=tab))
            else:
                tab = request.args.get('tab', 'upcoming')
                return redirect(url_for('admin_events', tab=tab))

    else:
        return render_template('403.html')

@app.route('/admin/orders', methods=['GET', 'POST'])
def admin_orders():
    if is_authenticated():
        if request.method == 'GET':
            page = int(request.args.get('page', 1))
            per_page = 8
            user_active = session['email_user']
            photo_card = aliased(EventPhoto)
            photo_page = aliased(EventPhoto)
            file_card = aliased(File)
            file_page = aliased(File)
            tab = request.args.get('tab', 'unpublished')
            q = request.args.get('q', '').strip()
            now = datetime.now()
            base_query = db.session.query(Event)
            if q:
                search = f"%{q.lower()}%"
                query = base_query.filter(
                    db.or_(
                        db.func.lower(Event.name).like(search),
                        db.cast(Event.id, db.String).like(f"%{q}%")
                    )
                )
                found = query.order_by(Event.event_date).all()
                # определяем, к какому табу относятся найденные ивенты
                if not found:
                    found_tab = None
                    events_info = []
                else:
                    # first event in found — определяем по дате и статусу в какой таб попадает
                    event = found[0]
                    if event.status == 'draft':
                        found_tab = 'unpublished'
                    elif event.event_date > now:
                        found_tab = 'upcoming'
                    else:
                        found_tab = 'past'
                    events_info = attach_images_to_events(found)
                unpublished_count = base_query.filter(Event.status == 'draft').count()
                # Пагинация вручную
                total = len(events_info)  # <= Вот это total!
                events_info = events_info[(page - 1) * per_page: page * per_page]  # Только текущая страница
                total_pages = math.ceil(total / per_page)
                return render_template('admin/orders.html',
                                       events_info=events_info,
                                       current_tab=found_tab,
                                       unpublished_count=unpublished_count,
                                       q=q, total_pages=total_pages, page=page, per_page=per_page,user_active=dict(session))
            else:
                # 1. Базовый запрос
                base_query = (
                    db.session.query(Event)
                    .outerjoin(photo_card, (photo_card.event_id == Event.id) & (photo_card.location == 'card'))
                    .outerjoin(file_card, file_card.id == photo_card.file_id)
                    .outerjoin(photo_page, (photo_page.event_id == Event.id) & (photo_page.location == 'page'))
                    .outerjoin(file_page, file_page.id == photo_page.file_id)
                    .add_columns(
                        file_card.id.label("card_filename"),
                        file_page.id.label("page_filename"),
                        file_card.originalname.label("card_ext"),
                        file_page.originalname.label("page_ext")
                    )
                )

                # 2. Фильтрация по табу
                if tab == 'upcoming':
                    base_query = base_query.filter(Event.event_date > now, Event.status != 'draft')
                elif tab == 'past':
                    base_query = base_query.filter(Event.event_date_end < now, Event.status != 'draft')
                elif tab == 'unpublished':
                    base_query = base_query.filter(Event.status == 'draft')

                # 3. Подсчет общего количества событий
                total_events = base_query.count()
                total_pages = (total_events + per_page - 1) // per_page

                # 4. Пагинация
                events = (
                    base_query
                    .order_by(Event.event_date)
                    .limit(per_page)
                    .offset((page - 1) * per_page)
                    .all()
                )

                events_info = []
                for event_obj, card_filename, page_filename, card_ext, page_ext in events:
                    event_obj.card_filename = str(card_filename)
                    event_obj.page_filename = str(page_filename)
                    event_obj.card_ext = get_extension(card_ext)
                    event_obj.page_ext = get_extension(page_ext)
                    events_info.append(event_obj)

                unpublished_count = db.session.query(Event).filter(Event.status == 'draft').count()

                return render_template(
                    'admin/orders.html',
                    user_active=dict(session),
                    today=(date.today() + timedelta(days=1)).isoformat(),
                    events_info=events_info,
                    current_tab=tab,
                    unpublished_count=unpublished_count,
                    page=page,
                    total_pages=total_pages
                )
        else:
            print(request.form)
            if request.form['action'] == 'add':
                event = db.session.query(Event).filter_by(id=request.form['event_id']).first()
                event.status = 'upcoming'
                db.session.commit()
                tab = request.args.get('tab', 'upcoming')
                return redirect(url_for('admin_events', tab=tab))
            elif request.form['action'] == 'delete':
                event = db.session.get(Event, request.form['event_id'])
                db.session.delete(event)
                #TODO добавить удаление файлов
                db.session.commit()
                tab = request.args.get('tab', 'unpublished')
                return redirect(url_for('admin_events', tab=tab))
            else:
                tab = request.args.get('tab', 'upcoming')
                return redirect(url_for('admin_events', tab=tab))

    else:
        return render_template('403.html')

@app.route('/admin/tickets', methods=['GET'])
def admin_tickets():
    if is_authenticated():
        user_active = session['email_user']
        events_info = (
            db.session.query(Event)
            .order_by(Event.id)
            .all()
        )
        users_info = (
            db.session.query(User)
            .order_by(User.id)
            .all()
        )
        tickets_info = (
            db.session.query(Ticket)
            .join(User, Ticket.user_id == User.id)
            .join(Event, Ticket.event_id == Event.id)
            .options(joinedload(Ticket.user), joinedload(Ticket.event))
            .order_by(Ticket.id)
            .all()
        )

        return render_template('admin/tickets.html', user_active=dict(session), events_info=events_info,
                               users_info=users_info, tickets_info=tickets_info)
    else:
        return render_template('403.html')

@app.route('/admin/qr_check_in', methods=['GET'])
def admin_qr_check_in():
    if is_authenticated():

        return render_template('admin/qr_scanner.html', user_active=dict(session))
    else:
        return render_template('403.html')

@app.route('/admin/deals', methods=['GET'])
def admin_deals():
    if is_authenticated():
        user_active = session['email_user']
        return render_template('admin/deals.html', user_active=dict(session))
    else:
        return render_template('403.html')


@app.route('/admin/tickets_request', methods=['GET'])
def admin_tickets_request():
    if is_authenticated():
        user_active = session['email_user']
        tickets_info = (
            db.session.query(Ticket)
            .join(User, Ticket.user_id == User.id)
            .join(Event, Ticket.event_id == Event.id)
            .options(joinedload(Ticket.user), joinedload(Ticket.event))
            .filter(Ticket.is_verified == False, Ticket.status != 'unverified')
            .order_by(Ticket.id)
            .all()
        )
        return render_template('admin/tickets_verification.html', user_active=dict(session), tickets_info=tickets_info)
    else:
        return render_template('403.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050, debug=True)
