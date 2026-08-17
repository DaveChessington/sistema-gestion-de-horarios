# IAM Microservice

## Overview

The **IAM (Identity & Access Management)** microservice provides authentication and authorization capabilities for the *Sistema de gestión de horarios* platform. It is built with **Flask 3.0**, uses **PostgreSQL** via SQLAlchemy for persistence, **bcrypt** for password hashing, and **JWT** for stateless token‑based authentication.

## Features

- **Administrative user registration** (`/register`) with bcrypt cost 12, strong password policy and role-based access control.
- Successful login migrates legacy Werkzeug hashes to bcrypt without invalidating existing credentials.
- **Scoped user administration** with listing, editing and logical deactivation.
- **Login** (`/login`) that returns a signed JWT.
- **Protected endpoints** using JWT (`/me`).
- **Role‑based access control** (`/admin-solo`) limited to `COORDINADOR` and `ADMIN_PLANTEL` roles.
- Comprehensive **unit / integration tests** in `tests/`.
- **Manual HTTP test suite** (`pruebas_manuales.http`) for quick verification with VS Code REST Client or Postman.
- **Database migrations** managed with **Flask-Migrate** (Alembic) — schema changes are versioned and applied automatically on container startup.

## Database Migrations (Flask-Migrate / Alembic)

This service uses **Flask-Migrate** (`Flask-Migrate==4.1.0`, `alembic==1.19.1`) to version-control all schema changes.  
Migrations live in `iam/migrations/versions/` and are applied automatically by `entrypoint.sh` on each container start.

### Migration commands (run from the `iam/` directory)

```powershell
# Activate the virtual environment first
.\venv\Scripts\activate

# Apply pending migrations (run on every deploy / container start)
flask --app app:create_app db upgrade

# Generate a new migration after changing models
flask --app app:create_app db migrate -m "describe the change"

# Downgrade one revision
flask --app app:create_app db downgrade -1

# Show current revision
flask --app app:create_app db current

# Show full migration history
flask --app app:create_app db history
```

> **Note:** `FLASK_APP` can also be set as an environment variable instead of using `--app`.  
> The `env.py` in `migrations/` is configured with `include_schemas=True` so Alembic tracks the `public` / `auth` PostgreSQL schemas.

## Quick Start (Docker)

```bash
# Build and start only IAM through Compose
docker compose up --build -d --no-deps iam
```

IAM listens on port `5000` inside its container. Compose exposes it on the host
at `http://localhost:5001/api/v1/auth` by default.

For a local virtual environment, install the base and security dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r iam\requirements.txt
.venv\Scripts\python.exe -m pip install -r iam\requirements-security.txt
```

## Environment Variables (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Secret used to sign JWTs. | `super-secret-key-udl` |
| `DATABASE_URL` | Full SQLAlchemy URL for PostgreSQL. | – (falls back to individual components) |
| `DB_USER` | DB username (used if `DATABASE_URL` not set). | `postgres` |
| `DB_PASSWORD` | DB password (used if `DATABASE_URL` not set). | `root` |
| `HOST` | DB host (used if `DATABASE_URL` not set). | `127.0.0.1` |
| `PORT` | DB port (used if `DATABASE_URL` not set). | `5432` |
| `DB_NAME` | Database name (used if `DATABASE_URL` not set). | `gestion_horaios_udl` |

Create a `.env` file in the `iam/` directory with the values you need before running the container.

## API Reference

| Method | Endpoint | Description | Protected? |
|--------|----------|-------------|-----------|
| `POST` | `/api/v1/auth/register` | Register a new user (requires `nombre`, `apellido`, `correo`, `password`, `rol`). | Yes (`COORDINADOR` or `ADMIN_PLANTEL`) |
| `POST` | `/api/v1/auth/login`    | Authenticate and receive a JWT. | No |
| `GET`  | `/api/v1/auth/users` | List users visible to the administrative account. | Yes (`COORDINADOR` or `ADMIN_PLANTEL`) |
| `GET`  | `/api/v1/auth/users/<id>` | Return one manageable user. | Yes (`COORDINADOR` or `ADMIN_PLANTEL`) |
| `PUT`  | `/api/v1/auth/users/<id>` | Update profile, role, plantel and optionally password. | Yes (`COORDINADOR` or `ADMIN_PLANTEL`) |
| `DELETE` | `/api/v1/auth/users/<id>` | Logically deactivate the account. | Yes (`COORDINADOR` or `ADMIN_PLANTEL`) |
| `GET`  | `/api/v1/auth/me`       | Return the payload of the supplied JWT. | Yes (`Bearer <token>`) |
| `GET`  | `/api/v1/auth/admin-solo` | Example admin‑only route (requires role `COORDINADOR` or `ADMIN_PLANTEL`). | Yes (`Bearer <token>`) |

`COORDINADOR` has global scope. `ADMIN_PLANTEL` can only list and manage users
assigned to its own plantel, cannot assign the `COORDINADOR` role and cannot
deactivate its own account. Deactivation preserves the record and prevents login.

### Example Request (cURL)

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:5001/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"correo":"admin@udl.edu.mx","password":"Password-Segura123!"}' | jq -r .token)

# Register (requires an administrative token)
curl -X POST http://localhost:5001/api/v1/auth/register \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"nombre":"Docente","apellido":"Nuevo","correo":"docente@udl.edu.mx","password":"Password-Segura123!","rol":"DOCENTE"}'

# Protected route
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/v1/auth/me
```

If the database has no administrative user yet, create the initial one through
the IAM CLI before using `/register`:

```bash
docker compose exec iam flask --app run:app create-admin --correo admin@udl.edu.mx
```

## Running Tests

### Automated tests

```bash
# From the iam directory
pytest tests/
```

### Manual tests

Open `iam/pruebas_manuales.http` in VS Code (REST Client) or import the requests into Postman. The file contains a full workflow covering registration, duplicate registration, login, role‑protected calls, and error cases.

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Make your changes and ensure all tests pass.
4. Push to your fork and open a Pull Request against the `development` branch.

Please follow the repository’s coding style and update the documentation if you add new endpoints.

## License

This microservice is part of the *Sistema de gestión de horarios* project and is licensed under the same terms as the parent repository (see the top‑level `LICENSE` file).
