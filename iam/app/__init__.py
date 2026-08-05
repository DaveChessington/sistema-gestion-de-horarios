from flask import Flask
from config import Config
from app.extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones
    db.init_app(app)

    # Registrar blueprints
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    # Registrar comandos CLI
    from app.commands import register_commands
    register_commands(app)

    # Crear tablas en el primer contexto
    with app.app_context():
        from app.models.plantel import Plantel
        from app.models.usuario import Usuario
        db.create_all()

    return app
