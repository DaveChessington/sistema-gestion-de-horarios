from app.extensions import db
from app.models.usuario import RolUsuario, Usuario
from app.services.catalog_client import CatalogClient
from app.utils.security import generate_token
import re


class AuthService:
    ALLOWED_ROLES = {role.value for role in RolUsuario}

    @staticmethod
    def _password_error(password):
        """Aplica la política fuerte compatible con el límite de bcrypt."""
        value = str(password)
        if len(value) < 12:
            return "La contraseña debe tener al menos 12 caracteres"
        if len(value.encode("utf-8")) > 72:
            return "La contraseña no puede superar 72 bytes"
        if not re.search(r"[A-Z]", value):
            return "La contraseña debe incluir una letra mayúscula"
        if not re.search(r"[a-z]", value):
            return "La contraseña debe incluir una letra minúscula"
        if not re.search(r"\d", value):
            return "La contraseña debe incluir un número"
        if not re.search(r"[^A-Za-z0-9]", value):
            return "La contraseña debe incluir un carácter especial"
        return None

    @staticmethod
    def _role_value(value):
        return value.value if isinstance(value, RolUsuario) else value

    @staticmethod
    def _actor_scope(actor):
        actor = actor or {}
        return actor.get("rol"), actor.get("id_plantel_asignado")

    @classmethod
    def _scope_error(cls, actor, target=None, requested_role=None, requested_plantel=None):
        actor_role, actor_plantel = cls._actor_scope(actor)
        if actor_role == "COORDINADOR":
            return None
        if actor_role != "ADMIN_PLANTEL" or actor_plantel is None:
            return "La cuenta no tiene un alcance administrativo válido"
        if target is not None:
            if cls._role_value(target.rol) == "COORDINADOR":
                return "Un administrador de plantel no puede administrar coordinadores"
            if str(target.id_plantel_asignado) != str(actor_plantel):
                return "No tienes permisos para administrar usuarios de otro plantel"
            if requested_role is None and requested_plantel is None:
                return None
        if requested_role == "COORDINADOR":
            return "Un administrador de plantel no puede asignar el rol COORDINADOR"
        if requested_plantel is None or str(requested_plantel) != str(actor_plantel):
            return "Solo puedes administrar usuarios de tu plantel asignado"
        return None

    @staticmethod
    def _validate_plantel(id_plantel_asignado):
        if id_plantel_asignado is None:
            return None
        try:
            if not CatalogClient.plantel_exists(id_plantel_asignado):
                return {"success": False, "error": "El id_plantel_asignado no existe en el catálogo", "status_code": 400}
        except Exception:
            return {"success": False, "error": "No se pudo validar el plantel asignado con el servicio de catálogo", "status_code": 502}
        return None

    @classmethod
    def register_user(cls, datos, actor=None):
        """Registra un usuario respetando el alcance de la cuenta administrativa."""
        for field in ("nombre", "apellido", "correo", "password", "rol"):
            if field not in datos or not str(datos[field]).strip():
                return {"success": False, "error": f"Falta el campo obligatorio: {field}", "status_code": 400}
        correo = str(datos["correo"]).strip().lower()
        if Usuario.query.filter(db.func.lower(Usuario.correo) == correo).first():
            return {"success": False, "error": "El correo ya está registrado", "status_code": 409}
        rol = str(datos["rol"]).strip().upper()
        if rol not in cls.ALLOWED_ROLES:
            return {"success": False, "error": "Rol inválido", "status_code": 400}
        password_error = cls._password_error(datos["password"])
        if password_error:
            return {"success": False, "error": password_error, "status_code": 400}
        id_plantel_asignado = datos.get("id_plantel_asignado")
        scope_error = cls._scope_error(actor, requested_role=rol, requested_plantel=id_plantel_asignado) if actor is not None else None
        if scope_error:
            return {"success": False, "error": scope_error, "status_code": 403}
        if rol == "ADMIN_PLANTEL" and id_plantel_asignado is None:
            return {"success": False, "error": "El administrador de plantel requiere una asignación", "status_code": 400}
        plantel_error = cls._validate_plantel(id_plantel_asignado)
        if plantel_error:
            return plantel_error
        nuevo_usuario = Usuario(
            nombre=str(datos["nombre"]).strip(), apellido=str(datos["apellido"]).strip(),
            correo=correo, rol=rol, id_plantel_asignado=id_plantel_asignado,
        )
        nuevo_usuario.set_password(datos["password"])
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            return {"success": True, "data": nuevo_usuario.to_dict(), "status_code": 201}
        except Exception:
            db.session.rollback()
            return {"success": False, "error": "Error interno al guardar en la base de datos", "status_code": 500}

    @classmethod
    def list_users(cls, actor):
        role, plantel_id = cls._actor_scope(actor)
        if role == "COORDINADOR":
            users = Usuario.query.order_by(Usuario.id_usuario).all()
        elif role == "ADMIN_PLANTEL" and plantel_id is not None:
            users = Usuario.query.filter(
                Usuario.id_plantel_asignado == plantel_id,
                Usuario.rol != RolUsuario.COORDINADOR,
            ).order_by(Usuario.id_usuario).all()
        else:
            return {"success": False, "error": "La cuenta no tiene un alcance administrativo válido", "status_code": 403}
        return {"success": True, "data": [user.to_dict() for user in users], "status_code": 200}

    @classmethod
    def get_user(cls, user_id, actor):
        user = db.session.get(Usuario, user_id)
        if user is None:
            return {"success": False, "error": "Usuario no encontrado", "status_code": 404}
        scope_error = cls._scope_error(actor, target=user)
        if scope_error:
            return {"success": False, "error": scope_error, "status_code": 403}
        return {"success": True, "data": user.to_dict(), "status_code": 200}

    @classmethod
    def update_user(cls, user_id, datos, actor):
        user = db.session.get(Usuario, user_id)
        if user is None:
            return {"success": False, "error": "Usuario no encontrado", "status_code": 404}
        scope_error = cls._scope_error(actor, target=user)
        if scope_error:
            return {"success": False, "error": scope_error, "status_code": 403}
        for field in ("nombre", "apellido", "correo", "rol"):
            if field not in datos or not str(datos[field]).strip():
                return {"success": False, "error": f"Falta el campo obligatorio: {field}", "status_code": 400}
        correo = str(datos["correo"]).strip().lower()
        duplicate = Usuario.query.filter(db.func.lower(Usuario.correo) == correo, Usuario.id_usuario != user_id).first()
        if duplicate:
            return {"success": False, "error": "El correo ya está registrado", "status_code": 409}
        rol = str(datos["rol"]).strip().upper()
        if rol not in cls.ALLOWED_ROLES:
            return {"success": False, "error": "Rol inválido", "status_code": 400}
        id_plantel_asignado = datos.get("id_plantel_asignado")
        scope_error = cls._scope_error(actor, requested_role=rol, requested_plantel=id_plantel_asignado)
        if scope_error:
            return {"success": False, "error": scope_error, "status_code": 403}
        if str(actor.get("id_usuario")) == str(user_id) and (
            rol != cls._role_value(user.rol) or str(id_plantel_asignado) != str(user.id_plantel_asignado)
        ):
            return {"success": False, "error": "No puedes cambiar tu propio rol o alcance durante la sesión", "status_code": 403}
        if rol == "ADMIN_PLANTEL" and id_plantel_asignado is None:
            return {"success": False, "error": "El administrador de plantel requiere una asignación", "status_code": 400}
        password = datos.get("password")
        password_error = cls._password_error(password) if password not in {None, ""} else None
        if password_error:
            return {"success": False, "error": password_error, "status_code": 400}
        plantel_error = cls._validate_plantel(id_plantel_asignado)
        if plantel_error:
            return plantel_error
        user.nombre = str(datos["nombre"]).strip()
        user.apellido = str(datos["apellido"]).strip()
        user.correo = correo
        user.rol = rol
        user.id_plantel_asignado = id_plantel_asignado
        if password:
            user.set_password(password)
        try:
            db.session.commit()
            return {"success": True, "data": user.to_dict(), "status_code": 200}
        except Exception:
            db.session.rollback()
            return {"success": False, "error": "Error interno al actualizar el usuario", "status_code": 500}

    @classmethod
    def deactivate_user(cls, user_id, actor):
        user = db.session.get(Usuario, user_id)
        if user is None:
            return {"success": False, "error": "Usuario no encontrado", "status_code": 404}
        if str(actor.get("id_usuario")) == str(user_id):
            return {"success": False, "error": "No puedes desactivar tu propia cuenta", "status_code": 403}
        scope_error = cls._scope_error(actor, target=user)
        if scope_error:
            return {"success": False, "error": scope_error, "status_code": 403}
        if not user.activo:
            return {"success": False, "error": "La cuenta ya se encuentra inactiva", "status_code": 409}
        user.activo = False
        try:
            db.session.commit()
            return {"success": True, "data": user.to_dict(), "status_code": 200}
        except Exception:
            db.session.rollback()
            return {"success": False, "error": "Error interno al desactivar el usuario", "status_code": 500}

    @staticmethod
    def login(correo, password):
        usuario = Usuario.query.filter_by(correo=correo).first()
        if not usuario or not usuario.check_password(password):
            return {"success": False, "error": "Credenciales inválidas", "status_code": 401}
        if not usuario.activo:
            return {"success": False, "error": "Cuenta de usuario inactiva", "status_code": 403}
        if usuario.password_needs_rehash:
            try:
                usuario.set_password(password)
                db.session.commit()
            except Exception:
                db.session.rollback()
                return {
                    "success": False,
                    "error": "No fue posible actualizar la protección de las credenciales",
                    "status_code": 500,
                }
        token = generate_token(usuario)
        return {"success": True, "token": token, "usuario": usuario.to_dict(), "status_code": 200}
