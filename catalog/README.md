# Catalog Microservice

## Overview

The **Catalog** microservice is part of the *Sistema de gestión de horarios* platform. It manages the core academic resources:
- **Planteles** (campuses/schools)
- **Salones** (classrooms)
- **Equipos** (hardware equipment)
- **Programas** (software programs)

It is built with **Flask 3.0**, uses **SQLAlchemy** with a PostgreSQL backend (schema `catalogos`), and follows a **tenant‑aware** permission model: users can only manipulate resources that belong to their assigned `id_plantel` unless they have a global role (`ADMINISTRADOR` or `COORDINADOR`).

---

## Models

| Model | Table (schema) | Key fields | Relationships |
|-------|----------------|------------|---------------|
| **Plantel** | `catalogos.planteles` | `id`, `nombre`, `direccion`, `activo` | One‑to‑many → **Salon** |
| **Salon**   | `catalogos.salones`   | `id_salon`, `numero`, `descripcion`, `capacidad`, `id_plantel`, `activo` | Many‑to‑one → **Plantel**; One‑to‑many → **Equipo** |
| **Equipo**  | `catalogos.equipos`   | `id_equipo`, `numero`, `descripcion`, `id_salon`, `activo` | Many‑to‑one → **Salon**; Many‑to‑many ↔ **Programa** (through `software_asociacion`) |
| **Programa**| `catalogos.programas` | `id_programa`, `nombre`, `descripcion`, `activo` | Many‑to‑many ↔ **Equipo** |

All models expose a convenient `to_dict()` method for JSON serialization and a `__repr__` for debugging.

---

## Endpoints (API v1)

All routes are mounted under `/api/v1` (see `catalog/app/routes/catalog_routes.py`).

### Planteles
| Method | URL | Description | Roles |
|--------|-----|-------------|-------|
| `POST`   | `/planteles` | Create a new plantel | `ADMINISTRADOR`, `COORDINADOR` |
| `GET`    | `/planteles` | List planteles (optional `active_only`) | Public |
| `GET`    | `/planteles/<int:id_plantel>` | Retrieve a plantel by ID | Public |
| `PUT`    | `/planteles/<int:id_plantel>` | Update plantel | `ADMINISTRADOR`, `COORDINADOR`, `ADMIN_PLANTEL` |
| `DELETE` | `/planteles/<int:id_plantel>` | Soft‑delete (set `activo=False`) | `ADMINISTRADOR`, `COORDINADOR`, `ADMIN_PLANTEL` |

### Salones
| Method | URL | Description | Roles |
|--------|-----|-------------|-------|
| `POST`   | `/salones` | Create a salon (requires `id_plantel`) | `ADMINISTRADOR`, `COORDINADOR`, `ADMIN_PLANTEL`, `ENCARGADO` |
| `GET`    | `/salones` | List salons with optional filters (`active_only`, `id_plantel`, `software_id`) | Public |
| `GET`    | `/salones/<int:id_salon>` | Retrieve a salon | Public |
| `PUT`    | `/salones/<int:id_salon>` | Update a salon | `ADMINISTRADOR`, `COORDINADOR`, `ADMIN_PLANTEL`, `ENCARGADO` |
| `DELETE` | `/salones/<int:id_salon>` | Soft‑delete a salon | Same as above |

### Equipos (Hardware)
| Method | URL | Description | Roles |
|--------|-----|-------------|-------|
| `POST`   | `/equipos` | Create equipment, optionally linked to a salon | `ADMINISTRADOR`, `COORDINADOR`, `ADMIN_PLANTEL`, `ENCARGADO` |
| `GET`    | `/equipos` | List equipment (filter by `id_salon`) | Public |
| `GET`    | `/equipos/<int:id_equipo>` | Retrieve equipment | Public |
| `PUT`    | `/equipos/<int:id_equipo>` | Update equipment | Same as `POST` |
| `DELETE` | `/equipos/<int:id_equipo>` | Soft‑delete equipment | Same as `POST` |
| `POST`   | `/equipos/<int:id_equipo>/software` | Assign a software program to an equipment | Same as `POST` |
| `DELETE` | `/equipos/<int:id_equipo>/software/<int:id_programa>` | Remove a software program from an equipment | Same as `POST` |

`ADMIN_PLANTEL` and `ENCARGADO` can only manage equipment associated with a
salon in their assigned plantel. Equipment without a salon has no tenant scope,
so creating, updating, deleting, or changing its software requires the global
`ADMINISTRADOR` or `COORDINADOR` role.

### Programas (Software)
| Method | URL | Description | Roles |
|--------|-----|-------------|-------|
| `POST`   | `/programas` | Create a software program | `ADMINISTRADOR`, `COORDINADOR`, `ADMIN_PLANTEL`, `ENCARGADO` |
| `GET`    | `/programas` | List programs | Public |
| `GET`    | `/programas/<int:id_programa>` | Retrieve a program | Public |
| `PUT`    | `/programas/<int:id_programa>` | Update program | Same as `POST` |
| `DELETE` | `/programas/<int:id_programa>` | Soft‑delete program | Same as `POST` |

All endpoints return JSON and use proper HTTP status codes (`201`, `200`, `400`, `403`, `404`, `500`). Permission checks are performed via:
- Flask decorators `@login_required` and `@require_roles`
- Service‑level helpers `check_user_plantel_access(...)` and
  `EquipmentService.check_user_access(...)`

---

## Tests

### Unit / Integration tests (`tests/`)
- **`test_catalog_service.py`** covers:
  - Creation of planteles, salones, equipos y programas.
  - Duplicate detection for equipment numbers.
  - Permission checks for **ENCARGADO** users (create/update/delete only within their own plantel).
  - Soft‑delete cascade behaviour (deactivating a plantel also deactivates its salones & equipos).
  - Public read‑only endpoints (no authentication required).
  - Retrieval of non‑existent entities raises `EntityNotFoundException`.

Run the suite with:
```powershell
$env:PYTHONPATH="."
python -m pytest -q
```
All tests pass (`8 passed`).

### Manual HTTP test suite (`catalog/pruebas_manuales.http`)
The file contains a full request workflow that can be executed with **httpie** or VS Code’s REST Client:
1. Obtain JWTs for each role (admin, encargado, docente, alumno).
2. Verify CRUD operations and permission boundaries for planteles, salones, equipos and programas.
3. Confirm correct status codes:
   - `201` on successful creation.
   - `403` when a user tries to act on a resource belonging to another plantel.
   - `200` on successful reads and soft‑deletes.
   - `400` for validation errors.
   - `401` when the token is missing or invalid.

Execute the suite (PowerShell) :
```powershell
Get-Content .\pruebas_manuales.http -Raw |
  http --default-scheme=http --default-port=5002 -f -b -t -r -v
```
The output will show each request and its response.

---

## How it Works

1. **Authentication** – Handled by the **IAM** service. The JWT payload includes `id_usuario`, `rol`, and `id_plantel` (or `id_plantel_asignado`).
2. **Authorization** – Each protected route decorates with `@login_required` (ensures a valid token) and `@require_roles(...)` (role‑based filter). Inside service methods, `check_user_plantel_access` enforces tenant isolation.
3. **Database** – All tables live in the PostgreSQL schema `catalogos`. The Flask app creates the schema on startup (`init_db`). Soft‑delete is implemented by setting the `activo` flag to `False`; cascade deactivation is performed manually in service methods.
4. **Error handling** – Custom exceptions (`EntityNotFoundException`, `DuplicateEntityException`, `InvalidDataException`, `PermissionDeniedException`) map to appropriate HTTP codes (404, 409, 400, 403). Unhandled errors fall back to a generic 500 response.

---

---

## Database Migrations (Flask-Migrate / Alembic)

This service uses **Flask-Migrate** (`Flask-Migrate==4.1.0`, `alembic==1.19.1`) to version-control all schema changes in the `catalogos` PostgreSQL schema.  
Migrations live in `catalog/migrations/versions/` and are applied automatically by `entrypoint.sh` on each container start.

### Migration commands (run from the project root)

```powershell
# Apply pending migrations (run on every deploy / container start)
$env:PYTHONPATH = "."
.\\catalog\\venv\\Scripts\\python.exe -m flask --app catalog.app:create_app db upgrade -d catalog/migrations

# Generate a new migration after changing models
.\\catalog\\venv\\Scripts\\python.exe -m flask --app catalog.app:create_app db migrate -d catalog/migrations -m "describe the change"

# Downgrade one revision
.\\catalog\\venv\\Scripts\\python.exe -m flask --app catalog.app:create_app db downgrade -1 -d catalog/migrations

# Show current revision
.\\catalog\\venv\\Scripts\\python.exe -m flask --app catalog.app:create_app db current -d catalog/migrations

# Show full migration history
.\\catalog\\venv\\Scripts\\python.exe -m flask --app catalog.app:create_app db history -d catalog/migrations
```

> **Note:** The `env.py` in `migrations/` is configured with `include_schemas=True` and `include_name` filtering to track only the `catalogos` schema, avoiding cross-schema false positives from `iam` or `booking`.

---

## Development

1. **Create a virtual environment** (already used in the repo):
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```
2. **Run the service** (catalog runs on port 5002):
```powershell
$env:FLASK_APP="catalog.app"
$env:FLASK_ENV="development"
flask run --port 5002
```
3. **Run the manual test suite** after the service starts (see above).
4. **Add new endpoints** – follow the existing pattern:
   - Add the route in `catalog_routes.py`.
   - Implement business logic in `catalog_service.py`.
   - Add permission checks via `@require_roles` and/or `check_user_plantel_access`.
   - Write unit tests under `tests/`.

---

## Contributing

Please follow the repository’s coding style, write docstrings, and keep the documentation up‑to‑date when adding new models or endpoints. Submit pull requests against the `development` branch.

---

## License

This microservice is part of the *Sistema de gestión de horarios* project and is licensed under the same terms as the top‑level `LICENSE` file.
