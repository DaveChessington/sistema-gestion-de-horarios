import pytest
from catalog.app import create_app
from catalog.config import Config
from catalog.app.extensions import db


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture(scope='session')
def catalog_app():
    app = create_app(config_class=TestConfig)
    return app


@pytest.fixture(scope='function')
def catalog_client(catalog_app):
    return catalog_app.test_client()


@pytest.fixture(scope='function')
def catalog_db(catalog_app):
    with catalog_app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()
