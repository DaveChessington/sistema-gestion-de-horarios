from app.extensions import db

class Plantel(db.Model):
    __tablename__ = 'planteles'
    __table_args__ = {'schema': 'catalogos'}

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relación uno a muchos con salones
    salones = db.relationship('Salon', backref='plantel', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'activo': self.activo
        }

    def __repr__(self):
        return f'<Plantel {self.nombre}>'
