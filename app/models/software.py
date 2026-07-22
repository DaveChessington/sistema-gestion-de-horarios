from app.extensions import db

# Tabla intermedia para la relación muchos a muchos de equipos y programas (software instalado)
software_asociacion = db.Table(
    'software',
    db.Column('id_equipo', db.Integer, db.ForeignKey('catalogos.equipos.id_equipo', ondelete='CASCADE'), primary_key=True),
    db.Column('id_programa', db.Integer, db.ForeignKey('catalogos.programas.id_programa', ondelete='CASCADE'), primary_key=True),
    schema='catalogos'
)
