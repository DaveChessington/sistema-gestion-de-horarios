from flask import Flask
from booking.config import Config
from booking.app.extensions import db, migrate
from booking.app.utils.db_init import init_db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar la extensión de base de datos y migraciones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registrar Blueprints
    from booking.app.routes.booking_routes import booking_bp
    from booking.app.routes.schedule_routes import schedule_bp
    
    app.register_blueprint(booking_bp, url_prefix='/api/v1')
    app.register_blueprint(schedule_bp, url_prefix='/api/v1')

    # Inicializar tablas y datos iniciales en el contexto de la aplicación
    with app.app_context():
        # Cargar modelos para asegurar su registro en SQLAlchemy metadata
        from booking.app.models import TipoEvento, Evento, Peticion
        init_db(app, db)

    return app
