"""Utilidades para inicialización de la base de datos y esquemas del módulo catalog.

Este archivo replica la estructura de `iam/app/utils/db_init.py` adaptada
para el esquema `catalogos` usado por el servicio `catalog`.
"""
from sqlalchemy import text


def create_schemas(db):
    """
    Crea los esquemas necesarios en la base de datos.
    
    Esquemas:
    - catalogos: Tablas relacionadas a catálogo (planteles, salones, equipos, programas)
    """
    schemas = ['catalogos']
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
        # Si es SQLite (pruebas), removemos el schema para evitar errores de SQLite en memoria
        if db.engine.url.drivername == 'sqlite':
            for table in db.metadata.tables.values():
                table.schema = None
        else:
            # Crear el esquema si no existe en PostgreSQL
            create_schemas(db)
        db.create_all()
        print("[OK] Esquema 'catalogos' y tablas inicializados correctamente")
