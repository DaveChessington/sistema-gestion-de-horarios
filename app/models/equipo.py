from app.extensions import db
from app.models.software import software_asociacion

class Equipo(db.Model):
    __tablename__ = 'equipos'

    id_equipo = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(100), unique=True, nullable=False, index=True)  # Número de inventario único
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    id_salon = db.Column(db.Integer, db.ForeignKey('salones.id_salon'), nullable=True)

    # Relación muchos a muchos con programas (software)
    programas = db.relationship(
        'Programa',
        secondary=software_asociacion,
        backref=db.backref('equipos', lazy=True)
    )

    def to_dict(self):
        return {
            'id_equipo': self.id_equipo,
            'numero': self.numero,
            'descripcion': self.descripcion,
            'activo': self.activo,
            'id_salon': self.id_salon,
            'programas': [p.to_dict() for p in self.programas if p.activo]
        }

    def __repr__(self):
        return f'<Equipo {self.numero}>'
