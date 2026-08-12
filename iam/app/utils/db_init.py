"""Utilidades para inicialización de la base de datos y esquemas."""
from sqlalchemy import text


def create_schemas(db):
    """
    Crea los esquemas necesarios en la base de datos.
    
    Esquemas:
    - auth: Tablas relacionadas a autenticación y usuarios
    - plantel: Tablas relacionadas a planteles
    """
    schemas = ['auth']
    
    with db.engine.connect() as connection:
        for schema in schemas:
            try:
                connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                connection.commit()
            except Exception as e:
                print(f"Error al crear esquema {schema}: {e}")


def init_db(app, db):
    """
    Inicializa la base de datos creando esquemas y tablas.
    
    Args:
        app: Instancia de Flask
        db: Instancia de SQLAlchemy
    """
    with app.app_context():
        # Crear esquemas primero
        create_schemas(db)
        
        # Crear todas las tablas
        db.create_all()
        
        print("✓ Esquemas y tablas inicializados correctamente")
