import uuid
from datetime import datetime
from sqlalchemy import VARCHAR, TEXT, DECIMAL, UUID
from extensions import db


class User(db.Model):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    email = db.Column(VARCHAR(255), unique=True, nullable=True)
    password_hash = db.Column(VARCHAR(255), nullable=False)
    phone_number = db.Column(VARCHAR(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    reset_token = db.Column(db.String, nullable=True)
    reset_token_exp = db.Column(db.DateTime, nullable=True)
    verification_code = db.Column(db.String, nullable=True)
    verification_code_exp = db.Column(db.DateTime, nullable=True)
    # nodes = db.relationship('Nodes', secondary='UserNodes', backref='users', lazy='selectin')
    # node_id = db.Column(db.String(36), unique=True)

    # transactions = db.relationship('Transaction', backref='users', cascade="all, delete")
    tickets = db.relationship('Ticket', backref='users', cascade="all, delete")
    # deals_as_buyer = db.relationship('Deal', backref='buyer', foreign_keys='Deal.buyer_id', cascade="all, delete")
    # deals_as_seller = db.relationship('Deal', backref='seller', foreign_keys='Deal.seller_id', cascade="all, delete")
    # recommended_events = db.relationship('RecommendedEvent', backref='user', cascade="all, delete")
    # user_balances = db.relationship('UserBalance', backref='user', cascade="all, delete")


class Genre(db.Model):
    __tablename__ = 'Genres'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)

class Cities(db.Model):
    __tablename__ = 'Cities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)

class Currencies(db.Model):
    __tablename__ = 'Currencies'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(VARCHAR(255), nullable=False)


class EventGenre(db.Model):
    __tablename__ = 'EventGenres'

    event_id = db.Column(db.Integer, primary_key=True)
    genre_id = db.Column(VARCHAR(255), nullable=False)


class Event(db.Model):
    __tablename__ = 'Events'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(VARCHAR(255), nullable=False)
    status = db.Column(db.Enum('draft', 'completed', 'published', name='EventStatus'), default='draft')
    tickets_available = db.Column(db.Integer, default=0)
    tickets_total = db.Column(db.Integer, default=0)
    date_start = db.Column(db.DateTime, nullable=False)
    date_end = db.Column(db.DateTime, nullable=False)
    location = db.Column(VARCHAR(255), nullable=True)
    address = db.Column(VARCHAR(255), nullable=True)
    city_id = db.Column(db.Integer)
    description = db.Column(TEXT, nullable=True)
    last_edit = db.Column(db.DateTime, nullable=False)
    tickets_prices = db.Column(DECIMAL(10, 2), nullable=False)
    photos = db.relationship('EventPhoto', backref='events', cascade="all, delete")
    tickets = db.relationship('Ticket', backref='events', cascade="all, delete")
    recommendations = db.relationship('RecommendedEvent', backref='events', cascade="all, delete")
    node_id = db.Column(
        db.String(36),
        db.ForeignKey('Nodes.id', ondelete='CASCADE'),
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
    __tablename__ = 'Tickets'

    id = db.Column(db.Integer, primary_key=True)
    buyer_user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='CASCADE'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('Events.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('available', 'sold', 'reserved', 'unverified', name='ticketstatus'), default='available')
    price = db.Column(DECIMAL(10, 2), nullable=False)
    description = db.Column(db.String, nullable=True)


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
    __tablename__ = 'EventPhotos'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('Events.id', ondelete='CASCADE'))
    file_id = db.Column(UUID(as_uuid=True), db.ForeignKey('Files.id', ondelete='CASCADE'))
    location = db.Column(VARCHAR(100), nullable=False)


class DealTicket(db.Model):
    __tablename__ = 'DealTicket'

    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('Deal.id', ondelete='CASCADE'))
    ticket_id = db.Column(db.Integer, db.ForeignKey('Ticket.id'), unique=True)


class RecommendedEvent(db.Model):
    __tablename__ = 'RecommendedEvents'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('Events.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('User.id', ondelete='CASCADE'), nullable=True)
    weight = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('event_id', 'user_id', name='_event_user_uc'),)


class File(db.Model):
    __tablename__ = 'Files'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bucket = db.Column(db.String, nullable=False)
    filename = db.Column(db.String, unique=True, nullable=False)
    originalname = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
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


class AdminUsers(db.Model):
    __tablename__ = 'AdminUsers'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(100))
    role = db.Column(db.String(100))
    user_hash = db.Column(db.String(100))
    # context_type = db.Column(db.String(100))
    # status = db.Column(db.String(100), default='Active')
    node_id = db.Column(
        db.String(36),
        db.ForeignKey('Nodes.id', ondelete='CASCADE'),
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )
    is_docs_verif = db.Column(db.Boolean, default=False)


class Nodes(db.Model):
    __tablename__ = 'Nodes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    slug = db.Column(db.String(100), unique=True)
    commission = db.Column(db.Integer)
    status = db.Column(db.Enum('active', 'archive', name='NodeStatus'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    main_organizer_id = db.Column(db.Integer)


class UserNode(db.Model):
    __tablename__ = 'UserNodes'
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    node_id = db.Column(UUID(as_uuid=True),
                        db.ForeignKey('Nodes.id', onupdate='CASCADE', ondelete='CASCADE'),
                        primary_key=True)
