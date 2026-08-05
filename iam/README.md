# IAM Microservice

## Overview

The **IAM (Identity & Access Management)** microservice provides authentication and authorization capabilities for the *Sistema de gestión de horarios* platform. It is built with **Flask 3.0**, uses **PostgreSQL** via SQLAlchemy for persistence, **bcrypt** for password hashing, and **JWT** for stateless token‑based authentication.

## Features

- **User registration** (`/register`) with secure password storage (`bcrypt`).
- **Login** (`/login`) that returns a signed JWT.
- **Protected endpoints** using JWT (`/me`).
- **Role‑based access control** (`/admin-solo`) limited to `COORDINADOR` and `ADMIN_PLANTEL` roles.
- Comprehensive **unit / integration tests** in `tests/`.
- **Manual HTTP test suite** (`pruebas_manuales.http`) for quick verification with VS Code REST Client or Postman.

## Quick Start (Docker)

```bash
# Build the image
docker build -t iam-service -f iam/Dockerfile .

# Run the container (exposes port 5000)
docker run -d -p 5000:5000 --name iam-service iam-service
```

The service will be reachable at `http://localhost:5000/api/v1/auth`.

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
| `POST` | `/api/v1/auth/register` | Register a new user (requires `nombre`, `apellido`, `correo`, `password`, `rol`). | No |
| `POST` | `/api/v1/auth/login`    | Authenticate and receive a JWT. | No |
| `GET`  | `/api/v1/auth/me`       | Return the payload of the supplied JWT. | Yes (`Bearer <token>`) |
| `GET`  | `/api/v1/auth/admin-solo` | Example admin‑only route (requires role `COORDINADOR` or `ADMIN_PLANTEL`). | Yes (`Bearer <token>`) |

### Example Request (cURL)

```bash
# Register
curl -X POST http://localhost:5000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"nombre":"Admin","apellido":"Sistema","correo":"admin@udl.edu.mx","password":"password123","rol":"COORDINADOR"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"correo":"admin@udl.edu.mx","password":"password123"}' | jq -r .token)

# Protected route
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/v1/auth/me
```

## Running Tests

### Automated tests

```bash
# From the project root
pytest iam/tests/
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
