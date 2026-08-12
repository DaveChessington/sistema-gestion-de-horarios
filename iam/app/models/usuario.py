import enum
from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

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
            'rol': self.rol.value if self.rol else None,
            'prioridad': self.rol.prioridad if self.rol else 0,
            'activo': self.activo,
            'id_plantel_asignado': self.id_plantel_asignado
        }

    def __repr__(self):
        return f'<Usuario {self.correo} ({self.rol.name if self.rol else "Sin Rol"})>'
