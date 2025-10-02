from flask_apscheduler import APScheduler
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import Event
from flask import current_app

scheduler = APScheduler()


@scheduler.task('interval', id='events_status_autoupdate', minutes=5)
def update_event_statuses():
    app = scheduler.app
    with app.app_context():
        try:
            #в 'past', где закончилось
            db.session.query(Event).filter(
                Event.date_end < func.now(),
                ~Event.status.in_(['completed', 'draft'])
            ).update({Event.status: 'completed'}, synchronize_session=False)
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Failed to autoupdate event statuses")