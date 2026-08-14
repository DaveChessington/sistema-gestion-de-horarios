from booking.app.extensions import db

class TipoEvento(db.Model):
    __tablename__ = 'tipo_evento'
    __table_args__ = {'schema': 'reservas'}

    id_tipo_evento = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    peso_evento = db.Column(db.Integer, nullable=False, default=10)
    descripcion = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id_tipo_evento': self.id_tipo_evento,
            'nombre': self.nombre,
            'peso_evento': self.peso_evento,
            'descripcion': self.descripcion
        }

    def __repr__(self):
        return f'<TipoEvento {self.nombre} (Peso: {self.peso_evento})>'
