"""Fábrica de la aplicación Flask dedicada al frontend."""

from flask import Flask

from schedule.config import Config


def create_app(config_class=Config):
    """Crea la capa de presentación sin acoplarla a los microservicios."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../frontend",
        static_url_path="",
    )
    app.config.from_object(config_class)

    from schedule.app.routes.public_routes import public_bp
    from schedule.app.routes.admin_routes import admin_bp
    from schedule.app.routes.legacy_routes import legacy_admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(legacy_admin_bp)
    return app
