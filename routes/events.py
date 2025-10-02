import math
import os
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP

from flask import Blueprint, session, render_template, flash, redirect, url_for, request, current_app
from sqlalchemy.orm import aliased
from werkzeug.utils import secure_filename

from extensions import db
from models import Nodes, EventPhoto, File, Event, Genre, EventGenre, Currencies, Cities
from routes.auth import is_authenticated
from routes.uploads import upload_file, get_upload_folder, get_extension

event_bp = Blueprint("events", __name__)


def format_last_edit(ts):
    now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
    if ts.date() == now.date():
        date_str = "today"
    elif ts.date() == (now - timedelta(days=1)).date():
        date_str = "yesterday"
    else:
        date_str = ts.strftime('%d %b %Y')
    time_str = ts.strftime('%H:%M')
    return f"Last edit {date_str} at {time_str}"


@event_bp.route('/admin/event/<int:event_id>', methods=['GET'])
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
        event_genres_info = (
            db.session.query(Genre)
            .join(EventGenre, EventGenre.genre_id == Genre.id)
            .filter(EventGenre.event_id == event_id)
            .order_by(Genre.name)
            .all()
        )

        date_format = (
            f"{event.date_start.strftime('%A, %d %B %Y')}  {event.date_start.strftime('%H:%M')} - {event.date_end.strftime('%H:%M')}"
        )
        genre_all_list = []
        for genre in genre_all:
            genre_all_list.append({"name": genre.name, "id": genre.id})
        last_edit = format_last_edit(event.last_edit)
        node_info = db.session.query(Nodes).filter(Nodes.id == session['node_id']).first()
        selling_fees = node_info.commission
        price = Decimal(str(event.tickets_prices))
        fee_pct = Decimal(str(selling_fees))
        event_genres = []

        cities = db.session.get(Cities, event.city_id)

        for genre in event_genres_info:
            event_genres.append({"name": genre.name, 'id': genre.id})
        buyer_will_pay = (price * fee_pct / Decimal('100')).quantize(Decimal('0.01'), ROUND_HALF_UP)
        return render_template('admin/events/event_info.html', event_genres=event_genres, event=event, date_format=date_format, city_name=cities.name,
                               genre_all_list=genre_all_list, last_edit=last_edit, selling_fees=selling_fees,
                               buyer_will_pay=buyer_will_pay, user_active=dict(session))
    else:
        return render_template('403.html')


@event_bp.route('/admin/event/edit/<int:event_id>', methods=['POST'])
def edit_dates_event(event_id):
    if is_authenticated():
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found', 'error')
            return redirect(url_for('events.info_event', event_id=event_id, user_active=dict(session)))
        data = request.get_json()
        event.date_start = data['start_date'] + ' ' + data['start_time']
        event.date_end = data['end_date'] + ' ' + data['end_time']
        db.session.commit()
        flash('Dates updated', 'success')
        return redirect(url_for('events.info_event', event_id=event_id, user_active=dict(session)))
    else:
        return render_template('403.html')


@event_bp.route('/admin/events/cancel', methods=['GET', 'POST'])
def cancel_event_creation():
    image_filename = session.pop('temp_image', None)
    session.pop('event_cover_path', None)
    UPLOAD_FOLDER = get_upload_folder()
    if image_filename:
        # защита от traversal: берём только basename
        safe_name = os.path.basename(image_filename)
        fpath = (UPLOAD_FOLDER / safe_name)

        try:
            root = UPLOAD_FOLDER.resolve()
            resolved = fpath.resolve()
            # убедимся, что файл действительно внутри upload_dir
            if str(resolved).startswith(str(root)) and resolved.is_file():
                try:
                    resolved.unlink()
                except FileNotFoundError:
                    pass
        except Exception as e:
            current_app.logger.warning("Failed to delete temp image %s: %s", fpath, e)
    flash('Черновик события очищен.', 'info')
    return redirect(url_for('events.admin_events'))


@event_bp.route('/admin/events/create', methods=['GET', 'POST'])
def create_event():
    if not is_authenticated():
        return render_template('403.html')
    UPLOAD_FOLDER = get_upload_folder()
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
            genres_str = request.form.get('genres', '')
            genres_list = [g.strip() for g in genres_str.split(',') if g.strip()]
            session['genres_list'] = genres_list
            cities_all = db.session.query(Cities).all()
            cities_list = []
            for city in cities_all:
                cities_list.append({'name': city.name, 'id': city.id})
            return render_template('admin/events/events_create_step_2.html', user_active=dict(session), cities_list=cities_list)
        elif request.form.get('step') == 'step_2':
            session['start_date'] = request.form.get('start_date')
            session['start_time'] = request.form.get('start_time')
            session['end_date'] = request.form.get('end_date')
            session['end_time'] = request.form.get('end_time')
            session['venue_name'] = request.form.get('venue_name')
            session['venue_city'] = request.form.get('venue_city')
            session['venue_address'] = request.form.get('venue_address')

            currency_all = db.session.query(Currencies).all()
            currency_list = []
            for currency in currency_all:
                currency_list.append({'name': currency.code, 'id': currency.id})
            return render_template('admin/events/events_create_step_3.html', user_active=dict(session), currency_list=currency_list)
        elif request.form.get('step') == 'step_3':
            try:

                available_quantity_tickets = request.form.get('available_quantity')
                price = request.form.get('price')
                # currency = request.form.get('currency_id')
                last_updated = datetime.now()
                # print(request.form.get('currency_id'))

                # TODO city в айди session['venue_city'] и currency_id
                start_dt = f"{session['start_date']} {session['start_time']}"
                end_dt = f"{session['end_date']} {session['end_time']}"
                event = Event(name=session['event_name'], tickets_available=available_quantity_tickets,
                              tickets_prices=price,
                              date_start=start_dt, location=session['venue_name'],
                              description=session['event_desc'], date_end=end_dt, address=session['venue_address'],
                              city_id=session['venue_city'], last_edit=last_updated, node_id=session['node_id'])
                db.session.add(event)
                db.session.flush()
                for genre in session['genres_list']:
                    db.session.add(EventGenre(event_id=event.id, genre_id=genre))

                db.session.commit()
                event_id = event.id
                filename = session.get('event_cover_path')
                # TODO Надо проработать фото
                if filename:
                    photo_card_id = upload_file(session['temp_image'], 'media')
                    db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='card'))
                    db.session.add(EventPhoto(event_id=event_id, file_id=photo_card_id, location='page'))
                db.session.commit()
            except Exception as e:
                print(e)
                return render_template('admin/events/events_create_step_3.html', user_active=dict(session), show_modal='error')
            return render_template('admin/events/events_create_step_3.html', user_active=dict(session), show_modal=True)

    filename = session.get('event_cover_path')
    event_image_url = None
    if filename:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            event_image_url = '/static/tmp/' + filename
        else:
            session.pop('event_cover_path')
    genre_all = db.session.query(Genre).all()
    genre_all_list = []
    for genre in genre_all:
        genre_all_list.append({'name': genre.name, 'id': genre.id})

    return render_template('admin/events/events_create_step_1.html', event_image_url=event_image_url,
                           user_active=dict(session), genre_all_list=genre_all_list)


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


@event_bp.route('/admin/events', methods=['GET', 'POST'])
def admin_events():
    if is_authenticated():
        if request.method == 'GET':
            page = int(request.args.get('page', 1))
            per_page = 8
            photo_card = aliased(EventPhoto)
            photo_page = aliased(EventPhoto)
            file_card = aliased(File)
            file_page = aliased(File)
            modal_success = request.args.get('modal_success', '').lower()
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
                total = len(events_info)
                events_info = events_info[(page - 1) * per_page: page * per_page]  # Только текущая страница
                total_pages = math.ceil(total / per_page)

                print(events_info)
                return render_template('admin/events/events.html',
                                       events_info=events_info,
                                       current_tab=found_tab,
                                       unpublished_count=unpublished_count,
                                       q=q, total_pages=total_pages, page=page, per_page=per_page,
                                       user_active=dict(session), modal_success=modal_success)
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

                city_map = db.session.query(Cities).all()
                for event in events_info:
                    for city in city_map:
                        if city.id == event.city_id:
                            event.city_name = city.name

                return render_template(
                    'admin/events/events.html',
                    user_active=dict(session),
                    today=(date.today() + timedelta(days=1)).isoformat(),
                    events_info=events_info,
                    current_tab=tab,
                    unpublished_count=unpublished_count,
                    page=page,
                    total_pages=total_pages, modal_success=modal_success
                )
        else:
            if request.form['action'] == 'add':
                event = db.session.query(Event).filter_by(id=request.form['event_id']).first()
                event.status = 'published'
                # TODO создать билеты
                db.session.commit()
                tab = request.args.get('tab', 'upcoming')
                return redirect(url_for('events.admin_events', tab=tab, modal_success=str(request.form['event_id'])))
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
