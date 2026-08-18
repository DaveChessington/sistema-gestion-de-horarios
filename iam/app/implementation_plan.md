# Plan de Implementación: Módulo 1 - IAM (Autenticación, Usuarios y Roles)

Este documento detalla el plan de trabajo para el Módulo 1 de Gestión de Identidad y Acceso (IAM) del Sistema de Gestión y Reservas de Espacios Universitarios. El diseño sigue un enfoque modular, escalable y separado por capas.

## 1. Responsabilidad Exacta del Módulo IAM
El módulo IAM será el guardián del sistema. Sus responsabilidades principales son:
- **Autenticación (Authn):** Verificar la identidad de los usuarios mediante correo y contraseña.
- **Autorización (Authz / RBAC):** Implementar un Control de Acceso Basado en Roles (RF-02) garantizando que los usuarios interactúen exclusivamente con los recursos permitidos para su rol (`COORDINADOR`, `ADMIN_PLANTEL`, `DOCENTE`, `ALUMNO`) y su `id_plantel_asignado`.
- **Seguridad de Credenciales:** Garantizar el cifrado unidireccional de contraseñas (RF-01) en reposo.
- **Gestión de Sesión:** Emitir y verificar tokens (JWT) o gestionar cookies de sesión segura para mantener el estado autenticado de las peticiones.

## 2. Entradas Esperadas
El módulo procesará los siguientes payloads principales (en formato JSON):
- **Login (`/auth/login`):**
  - `correo` (string, obligatorio)
  - `password` (string, texto plano, obligatorio)
- **Registro/Creación de Usuario (`/auth/register` o `/usuarios`):**
  - `nombre` (string, obligatorio)
  - `apellido` (string, obligatorio)
  - `correo` (string, válido, único)
  - `password` (string, texto plano, se procesará para hash)
  - `rol` (string, enum válido)
  - `id_plantel_asignado` (entero, FK de PostgreSQL)

## 3. Salidas Esperadas
Las respuestas estándar del API seguirán buenas prácticas REST:
- **Éxito en Login (200 OK):** Emisión de un Token (ej. JWT) en el body o en una cookie HttpOnly, además de información básica del perfil (ej. rol, plantel).
- **Éxito en Creación (201 Created):** Confirmación sin devolver datos sensibles (sin el password_hash).
- **Validación de Estado (`/auth/me`):** Retorno de la sesión actual activa (200 OK).
- **Logout (200 OK):** Invalidación de la sesión o cookie en el cliente/servidor.

## 4. Errores Críticos a Manejar
El módulo interceptará de forma limpia los siguientes casos:
- **`401 Unauthorized` (Credenciales Inválidas):** Contraseña incorrecta, correo inexistente, o ausencia de token en una ruta protegida.
- **`403 Forbidden` (Usuario Inactivo o Sin Permisos):** 
  - Intentos de inicio de sesión de usuarios con campo `activo=False`.
  - Violaciones de RBAC (ej. un DOCENTE intentando acceder a la administración del sistema).
- **`409 Conflict` (Duplicidad):** Intentos de registrar un usuario usando un `correo` que ya existe en la base de datos PostgreSQL.
- **`400 Bad Request`:** Payloads malformados (faltan campos obligatorios).

## 5. Funciones, Clases o Rutas de Flask Necesarias
Se utilizará la convención de Blueprints de Flask:
- **Rutas (Blueprints):**
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me` (Para obtener el contexto del usuario actual)
- **Decoradores Propios (Middlewares):**
  - `@login_required`: Verifica que el usuario tenga una sesión válida.
  - `@role_required(*roles_permitidos)`: Verifica que el usuario autenticado posea uno de los roles listados.
- **Servicios:**
  - `AuthService.login(correo, password)`: Orquesta la validación y generación de tokens.

## 6. Archivos Estructurales en el Espacio de Trabajo
Adoptaremos el patrón *Application Factory* con separación de responsabilidades:

```text
gestion_horarios_UDL/
├── app/
│   ├── __init__.py                # App Factory, configuración de Flask y SQLAlchemy
│   ├── extensions.py              # Instancias de db (SQLAlchemy), bcrypt/jwt
│   ├── models/
│   │   ├── usuario.py             # Modelo SQLAlchemy 'usuarios' (correo, password_hash, rol, etc.)
│   │   └── plantel.py             # Modelo SQLAlchemy 'planteles' (requerido para id_plantel_asignado)
│   ├── routes/
│   │   └── auth_routes.py         # Controladores (Flask Blueprints) para IAM
│   ├── services/
│   │   └── auth_service.py        # Lógica pura de negocio para auth y registro
│   └── utils/
│       └── security.py            # Decoradores RBAC (@role_required) y cifrado (werkzeug.security)
├── config.py                      # Variables de entorno (URI PostgreSQL, Secret Key)
└── run.py                         # Punto de entrada de la aplicación Flask
```

## 7. Relación con la Persistencia (PostgreSQL / SQLAlchemy)
Para **evitar la mezcla de lógica de negocio con consultas (Separation of Concerns)**:
1. **Modelos Anémicos/Ricos:** El modelo `Usuario` en `models/usuario.py` solo definirá las columnas y métodos utilitarios de la instancia (ej. `set_password()`, `check_password()`).
2. **Capa de Servicio:** El archivo `auth_service.py` será el único encargado de comunicarse con el objeto `db.session` de SQLAlchemy. Extraerá la información usando métodos como `Usuario.query.filter_by(correo=...).first()`.
3. **Controladores Limpios:** Las rutas de Flask (`auth_routes.py`) NO tendrán consultas SQL (ej. no habrá `db.session.add()` directamente en la ruta). Se limitarán a extraer el JSON del request, pasarlo al `AuthService`, y serializar la respuesta o el error en JSON para el cliente.

---
> [!IMPORTANT]
> **Aprobación Requerida**
> Por favor, revisa este diseño. Una vez que confirmes que estás de acuerdo con el alcance, responsabilidades, y estructura definida, procederé con la generación de código y la creación de los archivos paso a paso.
