"""Utilidades para inicialización de la base de datos y esquemas del módulo booking."""
from sqlalchemy import text


def create_schemas(db):
    """Crea el esquema 'reservas' en PostgreSQL si no existe."""
    schemas = ['reservas']
    with db.engine.connect() as connection:
        for schema in schemas:
            try:
                connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                connection.commit()
            except Exception as e:
                print(f"Error al crear esquema {schema}: {e}")


def seed_tipos_evento(db):
    """Siembra los tipos de eventos predeterminados con sus pesos de prioridad (E)."""
    from booking.app.models.tipo_evento import TipoEvento

    tipos_defecto = [
        {"id_tipo_evento": 1, "nombre": "Clase Curricular", "peso_evento": 50, "descripcion": "Clase regular impartida por docente"},
        {"id_tipo_evento": 2, "nombre": "Evento Institucional", "peso_evento": 40, "descripcion": "Evento organizado por dirección o administración"},
        {"id_tipo_evento": 3, "nombre": "Conferencia / Taller", "peso_evento": 30, "descripcion": "Conferencia, seminario o taller especial"},
        {"id_tipo_evento": 4, "nombre": "Sesión de Estudio (Grupal)", "peso_evento": 10, "descripcion": "Prácticas o estudio grupal de alumnos"},
    ]

    for data in tipos_defecto:
        existente = db.session.get(TipoEvento, data["id_tipo_evento"])
        if not existente:
            nuevo = TipoEvento(**data)
            db.session.add(nuevo)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error sembrando tipo_evento: {e}")


def init_db(app, db):
    """Inicializa la base de datos creando esquemas, tablas y datos iniciales."""
    with app.app_context():
        # Si es SQLite (para pruebas unitarias), removemos el schema para evitar incompatibilidad
        if db.engine.url.drivername == 'sqlite':
            for table in db.metadata.tables.values():
                table.schema = None
        else:
            create_schemas(db)
        
        db.create_all()
        seed_tipos_evento(db)
        print("✓ Esquema 'reservas' y tablas del módulo Booking inicializados correctamente.")
