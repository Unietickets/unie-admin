import os
import uuid
from datetime import datetime, date
import boto3
from flask import Flask, session, redirect, url_for, request, render_template, current_app
from sqlalchemy import VARCHAR, TEXT, DECIMAL, UUID
from sqlalchemy.orm import aliased, joinedload
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
load_dotenv()

db_host = os.getenv("MYSQL_HOST")
db_user = os.getenv("MYSQL_USER")
db_password = os.getenv("MYSQL_PASSWORD")
db_name = os.getenv("MYSQL_DB")
db_port = os.getenv("MYSQL_PORT")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
db = SQLAlchemy(app)

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

    transactions = db.relationship('Transaction', backref='user', cascade="all, delete")
    tickets = db.relationship('Ticket', backref='user', cascade="all, delete")
    deals_as_buyer = db.relationship('Deal', backref='buyer', foreign_keys='Deal.buyer_id', cascade="all, delete")
    deals_as_seller = db.relationship('Deal', backref='seller', foreign_keys='Deal.seller_id', cascade="all, delete")
    recommended_events = db.relationship('RecommendedEvent', backref='user', cascade="all, delete")
    user_balances = db.relationship('UserBalance', backref='user', cascade="all, delete")


class Event(db.Model):
    __tablename__ = 'Event'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)
    status = db.Column(db.Enum('coming', 'completed', 'cancelled', name='eventstatus'), default='coming')
    genre = db.Column(VARCHAR(100), nullable=True)
    tickets_available = db.Column(db.Integer, default=0)
    tickets_sold = db.Column(db.Integer, default=0)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(VARCHAR(255), nullable=True)
    description = db.Column(TEXT, nullable=True)
    photos = db.relationship('EventPhoto', backref='event', cascade="all, delete")
    tickets = db.relationship('Ticket', backref='event', cascade="all, delete")
    deals = db.relationship('Deal', backref='event', cascade="all, delete")
    recommendations = db.relationship('RecommendedEvent', backref='event', cascade="all, delete")


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
    user_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(100))
    user_hash = db.Column(db.String(100))


@app.context_processor
def utility_processor():
    def event_image_path(filename):
        absolute_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        if os.path.exists(absolute_path):
            return url_for('static', filename=f'uploads/{filename}')
        else:
            return url_for('static', filename='uploads/default.png')

    return dict(event_image_path=event_image_path)


@app.route('/')
def hello_world():
    return 'Hello World!'


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
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.user_id
            session['email_user'] = email
            session['role'] = user.role
            return redirect(url_for('stats'))
        else:
            return render_template('login.html')
    else:
        return render_template('login.html')


@app.route('/admin/stats')
def stats():
    if is_authenticated():
        user_active = session['email_user']
        return render_template('admin/stats.html', user_active=user_active)
    return render_template('403.html')


@app.route('/admin/users', methods=['GET'])
def admin_users():
    if is_authenticated():
        user_active = session['email_user']
        users_info = (
            db.session.query(User)
            .order_by(User.id)
            .all()
        )
        return render_template('admin/users.html', user_active=user_active, users_info=users_info)
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

@app.route('/admin/event/edit/<int:event_id>', methods=['POST'])
def edit_event(event_id):
    if is_authenticated():
        print(request.form)
        event = db.session.get(Event, event_id)
        event.name = request.form['name']
        event.status = request.form['status']
        event.genre = request.form['genre_id']
        event.event_date = request.form['event_date']
        event.location = request.form['location']
        event.description = request.form['description']
        db.session.commit()

        # Получаем файлы
        photo_card = request.files.get('photo_card')
        photo_page = request.files.get('photo_page')

        # Загружаем, если они действительно есть
        if photo_card and photo_card.filename:
            file_info = (
                db.session.query(EventPhoto)
                .filter(EventPhoto.location == 'card')
                .filter(EventPhoto.event_id == event_id)
                .first()
            )
            if file_info:
                old_file = file_info.file_id
                photo_card_id = upload_file(photo_card, 'media')
                file_info.file_id = photo_card_id
                db.session.commit()
                delete_file('media', old_file)
            else:
                photo_card_id = upload_file(photo_card, 'media')
                db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='card'))
                db.session.commit()
        if photo_page and photo_page.filename:
            file_info = (
                db.session.query(EventPhoto)
                .filter(EventPhoto.location == 'page')
                .filter(EventPhoto.event_id == event_id)
                .first()
            )
            if file_info:
                old_file = file_info.file_id
                photo_page_id = upload_file(photo_page, 'media')
                file_info.file_id = photo_page_id
                db.session.commit()
                delete_file('media', old_file)
            else:
                photo_page_id = upload_file(photo_page, 'media')
                db.session.add(EventPhoto(event_id=event_id, file_id=photo_page_id, location='page'))
                db.session.commit()
        return redirect(url_for('admin_events'))
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
        print(request.form)
        user = User(name=request.form['name'], email=request.form['email'],
                    password=generate_pass(request.form['password']),
                    is_active=True if request.form['is_active'] == 'true' else False,
                    phone_number=request.form['phone'])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('admin_users'))
    return render_template('403.html')


def upload_file(file, bucket):
    UPLOAD_DIR = "static/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    file_id = str(uuid.uuid4())
    local_filename = f"{file_id}{ext}"
    save_path = os.path.join(UPLOAD_DIR, local_filename)
    file.save(save_path)
    filename_in_s3 = f"events/{file_id}"
    # Определение реального размера файла
    file.stream.seek(0, 2)  # перейти в конец
    size = file.stream.tell()
    file.stream.seek(0)  # вернуть указатель в начало

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
        originalname=file.filename,
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


@app.route('/admin/events/create', methods=['POST'])
def create_event():
    if is_authenticated():
        event = Event(name=request.form['name'], status=request.form['status'], genre=request.form['genre_id'],
                      event_date=request.form['event_date'], location=request.form['location'],
                      description=request.form['description'])
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        # Получаем файлы
        photo_card = request.files.get('photo_card')
        photo_page = request.files.get('photo_page')

        # Загружаем, если они действительно есть
        if photo_card and photo_card.filename:
            photo_card_id = upload_file(photo_card, 'media')
            db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='card'))

        if photo_page and photo_page.filename:
            photo_page_id = upload_file(photo_page, 'media')
            db.session.add(EventPhoto(event_id=event_id, file_id=photo_page_id, location='page'))
        db.session.commit()
        return redirect(url_for('admin_events'))
    return render_template('403.html')


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


@app.route('/admin/events', methods=['GET'])
def admin_events():
    if is_authenticated():
        user_active = session['email_user']
        photo_card = aliased(EventPhoto)
        photo_page = aliased(EventPhoto)
        file_card = aliased(File)
        file_page = aliased(File)

        events = (
            db.session.query(Event)
            .outerjoin(photo_card, (photo_card.event_id == Event.id) & (photo_card.location == 'card'))
            .outerjoin(file_card, file_card.id == photo_card.file_id)
            .outerjoin(photo_page, (photo_page.event_id == Event.id) & (photo_page.location == 'page'))
            .outerjoin(file_page, file_page.id == photo_page.file_id)
            .order_by(Event.id)
            .add_columns(
                file_card.id.label("card_filename"),
                file_page.id.label("page_filename"),
                file_card.originalname.label("card_ext"),
                file_page.originalname.label("page_ext")
            )
            .all()
        )
        events_info = []
        for event_obj, card_filename, page_filename, card_ext, page_ext in events:
            event_obj.card_filename = str(card_filename)
            event_obj.page_filename = str(page_filename)
            event_obj.card_ext = get_extension(card_ext)
            event_obj.page_ext = get_extension(page_ext)
            events_info.append(event_obj)

        return render_template('admin/events.html', user_active=user_active, today=date.today().isoformat(),
                               events_info=events_info)
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

        return render_template('admin/tickets.html', user_active=user_active, events_info=events_info,
                               users_info=users_info, tickets_info=tickets_info)
    else:
        return render_template('403.html')


@app.route('/admin/deals', methods=['GET'])
def admin_deals():
    if is_authenticated():
        user_active = session['email_user']
        return render_template('admin/deals.html', user_active=user_active)
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
        return render_template('admin/tickets_verification.html', user_active=user_active, tickets_info=tickets_info)
    else:
        return render_template('403.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
