import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, current_app, url_for, render_template
from flask import session
from sqlalchemy import NullPool
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db
from mailer import mail
from models import AdminUsers
load_dotenv()


def register_user_loader(app):
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
        if request.endpoint in ('static', 'auth.admin_login', 'password_bp.forgot_password', 'password_bp.reset_password',):
            return
        user_id = session.get('user_id')
        if user_id:
            users_info = db.session.get(AdminUsers, user_id)
            if users_info.is_docs_verif == 'Banned':
                session.pop('user_id', None)
                return
            session['role'] = users_info.role
            if users_info.role == 'admin':
                session['context_type'] = 'root'
            else:
                session['context_type'] = 'node'
            return
        else:
            return render_template('403.html')


def create_app() -> Flask:
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    app.secret_key = b'_&adHJkaf"FauklkQ8z\n\xec]/'
    app.config.setdefault("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)  # 10 MB
    app.config.setdefault("ALLOWED_IMAGE_EXT", {"jpg", "jpeg", "png", "webp", "gif"})
    db_host = os.getenv("DATABASE_HOST")
    db_user = os.getenv("DATABASE_USER")
    db_password = os.getenv("DATABASE_PASSWORD")
    db_name = os.getenv("DATABASE_NAME")
    db_port = os.getenv("DATABASE_PORT")

    app.config.update(
        SQLALCHEMY_DATABASE_URI=f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
                                "?connect_timeout=5"
                                "&keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=3"
        ,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": NullPool,
            "pool_pre_ping": False,
        },
        SESSION_TYPE="filesystem",
        MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "465")),
        MAIL_USERNAME=os.getenv("MAIL_LOGIN", "exchangebots@gmail.com"),
        MAIL_PASSWORD=os.getenv("MAIL_PASS", "brhgvxncraffbceq"),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "false").lower() == "true",
        MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "true").lower() == "true",
        SECURITY_PASSWORD_SALT=os.getenv("SECURITY_PASSWORD_SALT", "brhgvxncraffbceq"),
    )
    upload_path = Path(app.root_path) / "static" / "tmp"
    upload_path.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = str(upload_path)
    db.init_app(app)
    mail.init_app(app)

    @app.teardown_appcontext
    def shutdown_session(exc=None):
        db.session.remove()

    # Блюпринты
    from routes.scheduler_task import scheduler
    from routes.admin_users import admin_users_registrator_bp
    from routes.api_cities import places_bp
    from routes.auth import auth_bp
    from routes.events import event_bp
    from routes.finances import finances_bp
    from routes.genres import genres_bp
    from routes.help import help_bp
    from routes.nodes import nodes_bp
    from routes.orders import orders_bp
    from routes.qr_check_in import qr_check_in_bp
    from routes.password import password_bp
    from routes.settings import settings_bp
    from routes.stats import stats_bp
    from routes.supports import supports_bp
    from routes.teams import teams_bp
    from routes.tickets import tickets_bp
    from routes.uploads import upload_bp
    from routes.users import clients_bp

    app.register_blueprint(admin_users_registrator_bp)
    app.register_blueprint(places_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(finances_bp)
    app.register_blueprint(genres_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(nodes_bp)
    app.register_blueprint(qr_check_in_bp)
    app.register_blueprint(password_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(supports_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(clients_bp)

    if not app.debug and not app.testing:
        scheduler.init_app(app)
        scheduler.start()

    register_user_loader(app)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
