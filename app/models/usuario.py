from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class RolUsuario(str, Enum):
    COORDINADOR = "COORDINADOR"
    ADMIN_PLANTEL = "ADMIN_PLANTEL"
    DOCENTE = "DOCENTE"
    ALUMNO = "ALUMNO"

    @property
    def prioridad(self):
        prioridades = {
            self.COORDINADOR: 4,
            self.ADMIN_PLANTEL: 3,
            self.DOCENTE: 2,
            self.ALUMNO: 0,
        }
        return prioridades[self]


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    rol = db.Column(db.Enum(RolUsuario), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    id_plantel_asignado = db.Column(db.Integer, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not password:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id_usuario": self.id_usuario,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "correo": self.correo,
            "rol": self.rol.value if isinstance(self.rol, RolUsuario) else self.rol,
            "activo": self.activo,
            "id_plantel_asignado": self.id_plantel_asignado,
        }
