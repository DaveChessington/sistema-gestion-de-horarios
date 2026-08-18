from flask import Flask
from catalog.config import Config
from catalog.app.extensions import db, migrate
from catalog.app.utils.db_init import init_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar base de datos y migraciones
    db.init_app(app)
    migrate.init_app(app, db)

    # Registrar Blueprints
    from catalog.app.routes.catalog_routes import catalog_bp
    app.register_blueprint(catalog_bp, url_prefix='/api/v1')

    # Crear esquemas y tablas en el primer contexto si no existen
    with app.app_context():
        # Importar modelos para asegurar registro en SQLAlchemy
        from catalog.app.models.plantel import Plantel
        from catalog.app.models.software import software_asociacion
        from catalog.app.models.salon import Salon
        from catalog.app.models.equipo import Equipo
        from catalog.app.models.programa import Programa

        # init_db crea el esquema 'catalogos' si hace falta y ejecuta db.create_all()
        init_db(app, db)

    return app
