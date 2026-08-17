from flask import Flask
from config import Config
from app.extensions import db, migrate
from app.utils.db_init import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registrar blueprints
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    # Registrar comandos CLI
    from app.commands import register_commands
    register_commands(app)

    # Crear tablas en el primer contexto
    with app.app_context():
        # Crear esquemas y luego todas las tablas
        init_db(app, db)

    return app
