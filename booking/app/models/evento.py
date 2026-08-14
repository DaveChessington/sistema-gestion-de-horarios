from booking.app.extensions import db

class Evento(db.Model):
    __tablename__ = 'evento'
    __table_args__ = {'schema': 'reservas'}

    id_evento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_apartado = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    
    id_salon = db.Column(db.Integer, nullable=False, index=True)
    id_tipo_evento = db.Column(db.Integer, db.ForeignKey('reservas.tipo_evento.id_tipo_evento'), nullable=False)
    id_usuario = db.Column(db.Integer, nullable=False)
    id_peticion = db.Column(db.Integer, nullable=True)
    prioridad = db.Column(db.Integer, nullable=False, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id_evento': self.id_evento,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'fecha_apartado': self.fecha_apartado.strftime('%Y-%m-%d') if self.fecha_apartado else None,
            'hora_inicio': self.hora_inicio.strftime('%H:%M:%S') if self.hora_inicio else None,
            'hora_fin': self.hora_fin.strftime('%H:%M:%S') if self.hora_fin else None,
            'id_salon': self.id_salon,
            'id_tipo_evento': self.id_tipo_evento,
            'id_usuario': self.id_usuario,
            'id_peticion': self.id_peticion,
            'prioridad': self.prioridad,
            'activo': self.activo
        }

    def __repr__(self):
        return f'<Evento {self.id_evento} | {self.nombre} | Salon {self.id_salon} | {self.fecha_apartado}>'
