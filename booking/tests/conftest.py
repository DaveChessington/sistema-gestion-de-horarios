import pytest
import jwt
from datetime import datetime, timedelta
from booking.app import create_app
from booking.config import Config
from booking.app.extensions import db


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'test-secret-key'


@pytest.fixture(scope='session')
def app():
    app = create_app(config_class=TestConfig)
    return app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    with app.app_context():
        db.create_all()
        # Sembrar tipos de eventos si no existen
        from booking.app.utils.db_init import seed_tipos_evento
        seed_tipos_evento(db)
        yield db
        db.session.remove()
        db.drop_all()


def make_token(id_usuario, rol, secret='test-secret-key'):
    payload = {
        'id_usuario': id_usuario,
        'correo': f'user_{id_usuario}@udl.edu.mx',
        'rol': rol,
        'id_plantel_asignado': 1,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, secret, algorithm='HS256')
