from flask import Flask
from config import Config
from app.extensions import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar base de datos
    db.init_app(app)

    # Registrar Blueprints
    from app.routes.catalog_routes import catalog_bp
    app.register_blueprint(catalog_bp, url_prefix='/api/v1')

    # Crear tablas en el primer contexto si no existen
    with app.app_context():
        # Importar modelos para asegurar registro en SQLAlchemy
        from app.models.plantel import Plantel
        from app.models.software import software_asociacion
        from app.models.salon import Salon
        from app.models.equipo import Equipo
        from app.models.programa import Programa
        
        db.create_all()

    return app
