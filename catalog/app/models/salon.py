from catalog.app.extensions import db

class Salon(db.Model):
    __tablename__ = 'salones'
    __table_args__ = {'schema': 'catalogos'}

    id_salon = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    capacidad = db.Column(db.Integer, nullable=False)
    id_plantel = db.Column(db.Integer, db.ForeignKey('catalogos.planteles.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relación uno a muchos con equipos
    equipos = db.relationship('Equipo', backref='salon', lazy=True)

    def to_dict(self):
        return {
            'id_salon': self.id_salon,
            'numero': self.numero,
            'descripcion': self.descripcion,
            'capacidad': self.capacidad,
            'id_plantel': self.id_plantel,
            'activo': self.activo
        }

    def __repr__(self):
        return f'<Salon {self.numero}>'
