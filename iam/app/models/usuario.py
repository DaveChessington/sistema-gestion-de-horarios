import enum
import bcrypt
from app.extensions import db
from werkzeug.security import check_password_hash as check_legacy_password_hash


BCRYPT_ROUNDS = 12
BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")

class RolUsuario(str,enum.Enum):
    COORDINADOR = "COORDINADOR"
    ADMIN_PLANTEL = "ADMIN_PLANTEL"
    DOCENTE = "DOCENTE"
    ALUMNO = "ALUMNO"

    @property
    def prioridad(self):
        """Devuelve el peso jerárquico del rol para resolver conflictos de horarios."""
        prioridades = {
            self.COORDINADOR: 4,
            self.ADMIN_PLANTEL: 3,
            self.DOCENTE: 2,
        }
        return prioridades.get(self, 0)

class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Campo rol usando el tipo Enum nativo de SQLAlchemy y Python
    rol = db.Column(db.Enum(RolUsuario), nullable=False)
    
    activo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Llave foránea hacia planteles
    id_plantel_asignado = db.Column(db.Integer, nullable=True)

    def set_password(self, password):
        """Genera un hash bcrypt con costo explícito de 12 rondas."""
        password_bytes = str(password).encode("utf-8")
        if len(password_bytes) > 72:
            raise ValueError("bcrypt admite contraseñas de hasta 72 bytes")
        self.password_hash = bcrypt.hashpw(
            password_bytes,
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode("utf-8")

    def check_password(self, password):
        """Verifica bcrypt y conserva compatibilidad con hashes Werkzeug."""
        if not self.password_hash:
            return False
        try:
            if self.is_bcrypt_hash:
                return bcrypt.checkpw(
                    str(password).encode("utf-8"),
                    self.password_hash.encode("utf-8"),
                )
            return check_legacy_password_hash(self.password_hash, str(password))
        except (TypeError, ValueError):
            return False

    @property
    def is_bcrypt_hash(self):
        return self.password_hash.startswith(BCRYPT_PREFIXES)

    @property
    def password_needs_rehash(self):
        """Detecta hashes heredados o bcrypt con un costo distinto de 12."""
        if not self.is_bcrypt_hash:
            return True
        try:
            return int(self.password_hash.split("$", 3)[2]) != BCRYPT_ROUNDS
        except (IndexError, TypeError, ValueError):
            return True

    def to_dict(self):
        """Retorna una representación segura en diccionario."""
        return {
            'id_usuario': self.id_usuario,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'correo': self.correo,
            'rol': self.rol.value if self.rol else None,
            'prioridad': self.rol.prioridad if self.rol else 0,
            'activo': self.activo,
            'id_plantel_asignado': self.id_plantel_asignado
        }

    def __repr__(self):
        return f'<Usuario {self.correo} ({self.rol.name if self.rol else "Sin Rol"})>'
