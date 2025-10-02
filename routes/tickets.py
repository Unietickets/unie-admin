from flask import url_for, redirect, Blueprint, request, render_template, session
from sqlalchemy.orm import joinedload

from extensions import db
from models import Ticket, Event, User
from routes.auth import is_authenticated

tickets_bp = Blueprint("tickets", __name__)


@tickets_bp.route('/admin/tickets/edit_status', methods=['GET'])
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
        return redirect(url_for('tickets.admin_tickets_request'))
    return render_template('403.html')


@tickets_bp.route('/admin/tickets/create', methods=['POST'])
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
        return redirect(url_for('tickets.admin_tickets'))
    return render_template('403.html')


@tickets_bp.route('/admin/tickets', methods=['GET'])
def admin_tickets():
    if is_authenticated():
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

        return render_template('admin/tickets/tickets.html', user_active=dict(session), events_info=events_info,
                               users_info=users_info, tickets_info=tickets_info)
    else:
        return render_template('403.html')

@tickets_bp.route('/admin/tickets_request', methods=['GET'])
def admin_tickets_request():
    if is_authenticated():
        tickets_info = (
            db.session.query(Ticket)
            .join(User, Ticket.user_id == User.id)
            .join(Event, Ticket.event_id == Event.id)
            .options(joinedload(Ticket.user), joinedload(Ticket.event))
            .filter(Ticket.is_verified == False, Ticket.status != 'unverified')
            .order_by(Ticket.id)
            .all()
        )
        return render_template('admin/tickets/tickets_verification.html', user_active=dict(session), tickets_info=tickets_info)
    else:
        return render_template('403.html')
