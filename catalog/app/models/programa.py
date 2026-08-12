from catalog.app.extensions import db

class Programa(db.Model):
    __tablename__ = 'programas'
    __table_args__ = {'schema': 'catalogos'}

    id_programa = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id_programa': self.id_programa,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'activo': self.activo
        }

    def __repr__(self):
        return f'<Programa {self.nombre}>'
