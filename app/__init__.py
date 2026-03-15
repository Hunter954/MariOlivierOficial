import os
from pathlib import Path
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para continuar.'
login_manager.login_message_category = 'info'


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    base_dir = Path(app.root_path).parent
    upload_dir = os.getenv('UPLOAD_DIR', '/data/uploads' if Path('/data').exists() else str(base_dir / 'app' / 'uploads'))
    database_url = os.getenv('DATABASE_URL', f"sqlite:///{base_dir / 'instance' / 'app.db'}")
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif database_url.startswith('postgresql://') and '+psycopg' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-change-me'),
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=upload_dir,
        MAX_CONTENT_LENGTH=512 * 1024 * 1024,
    )

    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from . import models
    from .routes import register_routes

    register_routes(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    with app.app_context():
        if os.getenv('AUTO_INIT_DB', 'true').lower() == 'true':
            db.create_all()
            models.seed_demo_data()

    return app
