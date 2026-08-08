import os
import sys
import pytest

# Make sure project root is on sys.path so `catalog` package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from catalog.app import create_app
from catalog.app.extensions import db
from catalog.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


@pytest.fixture(scope='session')
def app():
    app = create_app(config_class=TestConfig)
    return app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    # Ensure a clean database for each test function
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()
