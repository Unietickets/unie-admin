from flask import Blueprint, flash, redirect, url_for, request, render_template
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from routes.auth import is_authenticated
from extensions import db
from models import Event, EventGenre

genres_bp = Blueprint("genres", __name__)


@genres_bp.route('/admin/genre/edit/<int:event_id>/<string:genre_id>/<string:action>', methods=['POST'])
def edit_genre(event_id, genre_id, action):
    if is_authenticated():
        event = db.session.get(Event, event_id)

        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('events.info_event', event_id=event_id))
        genres = []
        if action == "add":
            if genre_id == "bulk":
                data = request.get_json()
                genres = [g for g in data.get('genres', [])]
            else:
                genres_info = db.session.get(EventGenre, event_id)
                for genres in genres_info:
                    if genre_id not in genres:
                        genres.append(genre_id)
            new_ids = [int(g) for g in genres]
            stmt = postgres_insert(EventGenre).values(
                [{"event_id": event.id, "genre_id": gid} for gid in new_ids]
            ).on_conflict_do_nothing(
                index_elements=["event_id", "genre_id"]
            )
            db.session.execute(stmt)
            db.session.commit()
        elif action == "delete":
            db.session.execute(
                delete(EventGenre).where(
                    EventGenre.event_id == event_id,
                    EventGenre.genre_id == genre_id
                )
            )
            db.session.commit()
        else:
            flash('Unknown action', 'error')
            return redirect(url_for('events.info_event', event_id=event_id))

        flash('Genre updated', 'success')
        return redirect(url_for('events.info_event', event_id=event_id))
    else:
        return render_template('403.html')