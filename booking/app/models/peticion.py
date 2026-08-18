from datetime import datetime, timezone
from booking.app.extensions import db

class Peticion(db.Model):
    __tablename__ = 'peticion'
    __table_args__ = {'schema': 'reservas'}

    id_peticion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Servidor/BD asigna la fecha en UTC de manera limpia
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha = db.Column(db.Date, nullable=False, index=True)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    estado = db.Column(db.String(30), nullable=False, default='PENDIENTE', index=True)
    
    id_usuario = db.Column(db.Integer, nullable=False, index=True)
    id_responsable = db.Column(db.Integer, nullable=False)
    id_salon = db.Column(db.Integer, nullable=False, index=True)
    id_programa = db.Column(db.Integer, nullable=True)
    materia_nombre = db.Column(db.String(150), nullable=True)
    numero_alumnos = db.Column(db.Integer, nullable=True)
    software_id = db.Column(db.Integer, nullable=True)
    id_tipo_evento = db.Column(db.Integer, db.ForeignKey('reservas.tipo_evento.id_tipo_evento'), nullable=False)
    
    prioridad_calculada = db.Column(db.Integer, nullable=False, default=0)
    observaciones = db.Column(db.Text, nullable=True)
    motivo_rechazo = db.Column(db.Text, nullable=True)
    
    id_evento = db.Column(db.Integer, db.ForeignKey('reservas.evento.id_evento'), nullable=True)

    # Relaciones de apoyo
    tipo_evento = db.relationship('TipoEvento', backref='peticiones', lazy=True)
    evento = db.relationship('Evento', foreign_keys=[id_evento], backref='peticiones_origen', lazy=True)

    @property
    def fecha_reserva(self):
        return self.fecha

    def to_dict(self):
        fecha_str = self.fecha.strftime('%Y-%m-%d') if self.fecha else None
        return {
            'id_peticion': self.id_peticion,
            'fecha_solicitud': self.fecha_solicitud.isoformat() if self.fecha_solicitud else None,
            'fecha': fecha_str,
            'fecha_reserva': fecha_str,
            'hora_inicio': self.hora_inicio.strftime('%H:%M:%S') if self.hora_inicio else None,
            'hora_fin': self.hora_fin.strftime('%H:%M:%S') if self.hora_fin else None,
            'estado': self.estado,
            'id_usuario': self.id_usuario,
            'id_responsable': self.id_responsable,
            'id_salon': self.id_salon,
            'id_programa': self.id_programa,
            'materia_nombre': self.materia_nombre,
            'numero_alumnos': self.numero_alumnos,
            'software_id': self.software_id,
            'id_tipo_evento': self.id_tipo_evento,
            'nombre_tipo_evento': self.tipo_evento.nombre if self.tipo_evento else None,
            'prioridad_calculada': self.prioridad_calculada,
            'observaciones': self.observaciones,
            'motivo_rechazo': self.motivo_rechazo,
            'id_evento': self.id_evento
        }

    def __repr__(self):
        return f'<Peticion {self.id_peticion} | Salon {self.id_salon} | {self.fecha} {self.hora_inicio}-{self.hora_fin} | {self.estado}>'
