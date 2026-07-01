from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(50), nullable=False) # COORDINADOR, ADMIN_PLANTEL, DOCENTE, ALUMNO
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Llave foránea hacia planteles
    id_plantel_asignado = db.Column(db.Integer, db.ForeignKey('planteles.id'), nullable=True)

    def set_password(self, password):
        """Genera el hash de la contraseña y lo almacena."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña dada coincide con el hash almacenado."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Retorna una representación segura en diccionario."""
        return {
            'id_usuario': self.id_usuario,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'correo': self.correo,
            'rol': self.rol,
            'activo': self.activo,
            'id_plantel_asignado': self.id_plantel_asignado
        }

    def __repr__(self):
        return f'<Usuario {self.correo} ({self.rol})>'
