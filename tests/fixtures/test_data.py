"""
Datos de prueba reutilizables para pruebas unitarias e integración.
"""

# ==========================================
# DATOS VÁLIDOS - REGISTRO
# ==========================================

USUARIO_ADMIN_VALIDO = {
    "nombre": "Carlos",
    "apellido": "García",
    "correo": "carlos.garcia@udl.edu.mx",
    "password": "SecurePass123!@",
    "rol": "COORDINADOR",
    "id_plantel_asignado": None
}

USUARIO_DOCENTE_VALIDO = {
    "nombre": "María",
    "apellido": "López",
    "correo": "maria.lopez@udl.edu.mx",
    "password": "DocPass456#@",
    "rol": "DOCENTE",
    "id_plantel_asignado": 1
}

USUARIO_ALUMNO_VALIDO = {
    "nombre": "Pedro",
    "apellido": "Martínez",
    "correo": "pedro.martinez@udl.edu.mx",
    "password": "AlumPass789$",
    "rol": "ALUMNO"
}

USUARIO_ADMIN_PLANTEL_VALIDO = {
    "nombre": "Luis",
    "apellido": "Sánchez",
    "correo": "luis.sanchez@udl.edu.mx",
    "password": "AdminPlantel123!",
    "rol": "ADMIN_PLANTEL",
    "id_plantel_asignado": 2
}

# ==========================================
# DATOS INVÁLIDOS - REGISTRO
# ==========================================

USUARIO_CORREO_DUPLICADO = {
    "nombre": "Otro",
    "apellido": "Usuario",
    "correo": "carlos.garcia@udl.edu.mx",  # Ya registrado
    "password": "DifferentPass123!",
    "rol": "DOCENTE"
}

USUARIO_ROL_INVALIDO = {
    "nombre": "Test",
    "apellido": "User",
    "correo": "test.invalid@udl.edu.mx",
    "password": "TestPass123!",
    "rol": "SUPERADMIN"  # No existe
}

USUARIO_CAMPOS_FALTANTES = {
    "nombre": "Incompleto",
    "apellido": "Usuario"
    # Faltan: correo, password, rol
}

USUARIO_PASSWORD_VACIA = {
    "nombre": "Test",
    "apellido": "User",
    "correo": "test.vacia@udl.edu.mx",
    "password": "",
    "rol": "ALUMNO"
}

USUARIO_PASSWORD_MUY_CORTA = {
    "nombre": "Test",
    "apellido": "User",
    "correo": "test.corta@udl.edu.mx",
    "password": "123",
    "rol": "ALUMNO"
}

USUARIO_NOMBRE_MUY_LARGO = {
    "nombre": "A" * 200,
    "apellido": "Usuario",
    "correo": "test.largo@udl.edu.mx",
    "password": "TestPass123!",
    "rol": "ALUMNO"
}

USUARIO_CORREO_INVALIDO = {
    "nombre": "Test",
    "apellido": "User",
    "correo": "notanemail",
    "password": "TestPass123!",
    "rol": "ALUMNO"
}

# ==========================================
# DATOS VÁLIDOS - LOGIN
# ==========================================

LOGIN_ADMIN_VALIDO = {
    "correo": "carlos.garcia@udl.edu.mx",
    "password": "SecurePass123!@"
}

LOGIN_DOCENTE_VALIDO = {
    "correo": "maria.lopez@udl.edu.mx",
    "password": "DocPass456#@"
}

# ==========================================
# DATOS INVÁLIDOS - LOGIN
# ==========================================

LOGIN_PASSWORD_INCORRECTO = {
    "correo": "carlos.garcia@udl.edu.mx",
    "password": "WrongPass123"
}

LOGIN_CORREO_INEXISTENTE = {
    "correo": "noexiste@udl.edu.mx",
    "password": "AnyPass123"
}

LOGIN_CREDENCIALES_VACIAS = {
    "correo": "",
    "password": ""
}

LOGIN_SIN_PASSWORD = {
    "correo": "carlos.garcia@udl.edu.mx"
    # Falta password
}

LOGIN_SIN_CORREO = {
    "password": "SecurePass123!@"
    # Falta correo
}

# ==========================================
# CONSTANTES DE ROLES
# ==========================================

ROLES_VALIDOS = ["COORDINADOR", "ADMIN_PLANTEL", "DOCENTE", "ALUMNO"]
ROLES_INVALIDOS = ["SUPERADMIN", "HACKER", "GUEST", "UNKNOWN"]

# ==========================================
# CONSTANTES DE PRIORIDADES
# ==========================================

PRIORIDADES_ROLES = {
    "COORDINADOR": 4,
    "ADMIN_PLANTEL": 3,
    "DOCENTE": 2,
    "ALUMNO": 0
}
