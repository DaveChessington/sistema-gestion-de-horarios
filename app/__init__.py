from flask import Flask


def create_app(config_object=None):
    app = Flask(__name__)
    if config_object is None:
        from config import Config

        app.config.from_object(Config)
    else:
        app.config.from_object(config_object)

    from app.extensions import db

    db.init_app(app)

    from app.routes.auth_routes import auth_bp

    app.register_blueprint(auth_bp)

    return app
