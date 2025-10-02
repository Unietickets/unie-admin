import math
from datetime import datetime, timedelta, date

from flask import Blueprint, session, render_template, redirect, url_for, request
from sqlalchemy.orm import aliased

from extensions import db
from models import EventPhoto, File, Event
from routes.auth import is_authenticated
from routes.events import attach_images_to_events
from routes.uploads import get_extension

orders_bp = Blueprint("orders", __name__)


@orders_bp.route('/admin/orders', methods=['GET', 'POST'])
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
                found = query.order_by(Event.date_start).all()
                # определяем, к какому табу относятся найденные ивенты
                if not found:
                    found_tab = None
                    events_info = []
                else:
                    # first event in found — определяем по дате и статусу в какой таб попадает
                    event = found[0]
                    if event.status == 'draft':
                        found_tab = 'unpublished'
                    elif event.date_start > now:
                        found_tab = 'upcoming'
                    else:
                        found_tab = 'past'
                    events_info = attach_images_to_events(found)
                unpublished_count = base_query.filter(Event.status == 'draft').count()
                # Пагинация вручную
                total = len(events_info)  # <= Вот это total!
                events_info = events_info[(page - 1) * per_page: page * per_page]  # Только текущая страница
                total_pages = math.ceil(total / per_page)
                return render_template('admin/orders/orders.html',
                                       events_info=events_info,
                                       current_tab=found_tab,
                                       unpublished_count=unpublished_count,
                                       q=q, total_pages=total_pages, page=page, per_page=per_page,
                                       user_active=dict(session))
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
                    base_query = base_query.filter(Event.date_start > now, Event.status != 'draft')
                elif tab == 'past':
                    base_query = base_query.filter(Event.date_end < now, Event.status != 'draft')
                elif tab == 'unpublished':
                    base_query = base_query.filter(Event.status == 'draft')

                # 3. Подсчет общего количества событий
                total_events = base_query.count()
                total_pages = (total_events + per_page - 1) // per_page

                # 4. Пагинация
                events = (
                    base_query
                    .order_by(Event.date_start)
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
                    'admin/orders/orders.html',
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
                return redirect(url_for('events.admin_events', tab=tab))
            elif request.form['action'] == 'delete':
                event = db.session.get(Event, request.form['event_id'])
                db.session.delete(event)
                # TODO добавить удаление файлов
                db.session.commit()
                tab = request.args.get('tab', 'unpublished')
                return redirect(url_for('events.admin_events', tab=tab))
            else:
                tab = request.args.get('tab', 'upcoming')
                return redirect(url_for('events.admin_events', tab=tab))

    else:
        return render_template('403.html')
