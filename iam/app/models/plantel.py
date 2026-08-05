from app.extensions import db

class Plantel(db.Model):
    __tablename__ = 'planteles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(255), nullable=True)

    # Relación uno a muchos con usuarios
    usuarios = db.relationship('Usuario', backref='plantel_asignado', lazy=True)

    def __repr__(self):
        return f'<Plantel {self.nombre}>'
