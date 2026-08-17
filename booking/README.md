# Booking Microservice

## Overview

The **Booking** (Reservas y Horarios) microservice is part of the *Sistema de gestión de horarios* platform. It manages classroom space requests, automatic schedule collision resolution using a dynamic priority algorithm, confirmed calendar events, and schedule grid availability queries.

Key features:
- Built with **Flask 3.0** and **SQLAlchemy**.
- Uses **PostgreSQL** as the primary persistence engine (schema `reservas`).
- Integrated with **IAM** microservice for stateless JWT authentication (`Bearer <token>`).
- Intercommunicates with **Catalog** microservice (`CATALOG_SERVICE_URL`) for real-time room existence and capacity verification.
- Enforces `ADMIN_PLANTEL` tenant scope against Catalog for creation, history, and cancellation operations.
- **Concurrency control** with pessimistic row locking (`SELECT ... FOR UPDATE`) to eliminate double-booking race conditions.
- Automated priority calculation ($P = U + E$) and **FIFO displacement logic**.

---

## Models

All models reside in the PostgreSQL schema `reservas` and expose `to_dict()` methods for JSON serialization:

| Model | Table (schema) | Key fields | Description / Relationships |
|-------|----------------|------------|-----------------------------|
| **TipoEvento** | `reservas.tipo_evento` | `id_tipo_evento`, `nombre`, `peso_evento`, `descripcion` | Preseeded event categories with assigned priority weights ($E$). One-to-many $\rightarrow$ **Peticion**, **Evento**. |
| **Peticion** | `reservas.peticion` | `id_peticion`, `fecha_solicitud`, `fecha`, `hora_inicio`, `hora_fin`, `estado`, `id_usuario`, `id_responsable`, `id_salon`, `id_programa`, `materia_nombre`, `numero_alumnos`, `id_tipo_evento`, `prioridad_calculada`, `observaciones`, `motivo_rechazo`, `id_evento` | Audit log and lifecycle tracking of reservation requests (`APROBADA`, `PENDIENTE`, `RECHAZADA`, `DESPLAZADA`, `CANCELADA`). |
| **Reserva (Evento)** | `reservas.evento` | `id_evento`, `nombre`, `descripcion`, `fecha`, `hora_inicio`, `hora_fin`, `id_salon`, `numero_alumnos`, `id_tipo_evento`, `id_usuario`, `id_peticion`, `prioridad`, `activo` | Confirmed occupancy on the academic calendar. `Evento` is retained as the physical model name for compatibility and exposed as the `Reserva` domain alias. |

---

## Priority Algorithm & Collision Rules

When a user submits a booking request, the service computes a total priority score $P$:

$$P = U + E$$

### 1. User Role Weight ($U$)
- `COORDINADOR` / `DOCENTE` / `PROFESOR` / `MAESTRO`: **40**
- `ADMIN_PLANTEL` / `ENCARGADO` / `ADMINISTRADOR`: **30**
- `ALUMNO` / `ESTUDIANTE`: **10**

### 2. Event Type Weight ($E$)
- **Clase Curricular** (`id_tipo_evento = 1`): **50**
- **Evento Institucional** (`id_tipo_evento = 2`): **40**
- **Conferencia / Taller** (`id_tipo_evento = 3`): **30**
- **Sesión de Estudio (Grupal)** (`id_tipo_evento = 4`): **10**

### 3. Collision Resolution Strategy
When an incoming request overlaps in time (`hora_inicio < fin_nuevo` and `hora_fin > inicio_nuevo`) for the same `id_salon` and `fecha`:

- **Free Schedule**: Automatically approved (`estado = 'APROBADA'`) and creates an active `Evento`.
- **Higher Priority Overlap ($P_{\text{nueva}} > P_{\text{existente}}$)**: Incoming request displaces overlapping reservations of lower priority. Overlapped requests transition to `DESPLAZADA` (storing a rejection reason), their corresponding `Evento` records are deactivated (`activo = False`), and the new request is `APROBADA`.
- **Equal or Lower Priority Overlap ($P_{\text{nueva}} \le P_{\text{existente}}$)**: Incoming request is rejected (`estado = 'RECHAZADA'`) returning **HTTP 409 Conflict** under the **FIFO (First-In, First-Out)** rule.

---

## Docker Compose

From the project root, build and start only Booking without recreating its
running dependencies:

```bash
docker compose up -d --no-deps --build booking
```

The service is available at `http://localhost:5003/api/v1` by default.
Inside the Compose network it connects to PostgreSQL through `postgres_db` and
to Catalog through `http://catalog:5002`.

---

## Environment Variables (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask app secret key. | `secret-key-booking-udl` |
| `JWT_SECRET_KEY` | Secret key used to decode JWTs issued by IAM. | `super-secret-key-udl` |
| `DATABASE_URL` | Full SQLAlchemy URI for PostgreSQL. | `postgresql+psycopg://postgres:root@127.0.0.1:5432/gestion_horarios_udl` |
| `DB_USER` | DB username (used if `DATABASE_URL` is not set). | `postgres` |
| `DB_PASSWORD` | DB password (used if `DATABASE_URL` is not set). | `root` |
| `DB_HOST` | DB host (used if `DATABASE_URL` is not set). | `127.0.0.1` |
| `DB_PORT` | DB port (used if `DATABASE_URL` is not set). | `5432` |
| `DB_NAME` | Database name (used if `DATABASE_URL` is not set). | `gestion_horarios_udl` |
| `BOOKING_PORT` | Host port exposed by Compose for Booking. | `5003` |
| `CATALOG_SERVICE_URL` | Base URL of Catalog microservice for room validation. | `http://127.0.0.1:5002` |
| `CATALOG_REQUEST_TIMEOUT` | Maximum seconds to wait while resolving Plantel scope in Catalog. | `5` |

---

## API Reference

All routes are mounted under `/api/v1`.

| Method | Endpoint | Description | Protected? |
|--------|----------|-------------|-----------|
| `POST` | `/api/v1/booking/request` | Submit classroom booking request with automatic capacity and priority collision handling. | Yes (`Bearer <token>`) |
| `GET` | `/api/v1/booking/request/<int:id_peticion>` | Retrieve one request within the authenticated user's scope. | Yes (`Bearer <token>`) |
| `PATCH` / `PUT` | `/api/v1/booking/request/<int:id_peticion>` | Reprogram a request atomically and reapply capacity, priority and collision rules. | Yes (`Bearer <token>`) |
| `GET` | `/api/v1/booking/history` | Retrieve booking request history with filters (`estado`, `id_salon`, `fecha`, `id_usuario`). | Yes (`Bearer <token>`) |
| `DELETE` | `/api/v1/booking/request/<int:id_peticion>` | Cancel a booking request, liberate classroom slot, and deactivate associated event. | Yes (`Bearer <token>`) |
| `GET` | `/api/v1/schedule/grid` | Query occupancy schedule grid matrix in JSON format. | Public |

---

## Endpoint Details & Purpose

### 1. `POST /api/v1/booking/request`
- **Purpose**: Submits a new booking request. Performs real-time room validation against Catalog Service (`GET /api/v1/salones/<id_salon>`), verifies capacity against `numero_alumnos`, applies pessimistic locking (`SELECT FOR UPDATE`), evaluates priority $P = U + E$, and atomically registers or displaces bookings.
- **Permissions**: `ADMIN_PLANTEL` can only submit requests for Salones belonging to `id_plantel_asignado` from its JWT. `COORDINADOR` retains global scope.
- **Request Body**:
```json
{
  "id_salon": 101,
  "id_programa": 1,
  "materia_nombre": "Base de Datos Avanzada",
  "fecha_reserva": "2026-09-15",
  "hora_inicio": "08:00",
  "hora_fin": "10:00",
  "id_tipo_evento": 1,
  "numero_alumnos": 25,
  "observaciones": "Requiere proyector y red empresarial"
}
```
- **Responses**:
  - `201 Created`: Request approved directly or approved by displacing lower-priority bookings.
  - `400 Bad Request`: Missing mandatory fields, invalid hours (`hora_inicio >= hora_fin`), capacity exceeded, or invalid room.
  - `409 Conflict`: Request rejected because of an existing booking with equal or higher priority (FIFO rule).
  - `503 Service Unavailable`: Cannot connect to Catalog microservice.

---

### 2. `GET /api/v1/booking/history`
- **Purpose**: Consults booking history. 
  - Regular users (`DOCENTE`, `ALUMNO`) only see their own requests.
  - `COORDINADOR` can view all requests or filter by a specific `id_usuario`.
  - `ADMIN_PLANTEL` can only view requests for Salones belonging to its assigned Plantel, including inactive historical Salones.
- **Query Parameters**:
  - `estado`: Filter by request state (`APROBADA`, `PENDIENTE`, `RECHAZADA`, `DESPLAZADA`, `CANCELADA`).
  - `id_salon`: Filter by classroom ID.
  - `fecha` / `fecha_reserva`: Filter by date (`YYYY-MM-DD`).
  - `id_usuario`: Filter by user ID (Admin only).
- **Response** (`200 OK`):
```json
{
  "total": 1,
  "peticiones": [
    {
      "id_peticion": 1,
      "fecha_solicitud": "2026-08-16T15:00:00",
      "fecha_reserva": "2026-09-15",
      "hora_inicio": "08:00:00",
      "hora_fin": "10:00:00",
      "estado": "APROBADA",
      "id_usuario": 10,
      "id_salon": 101,
      "materia_nombre": "Base de Datos Avanzada",
      "prioridad_calculada": 90,
      "nombre_tipo_evento": "Clase Curricular"
    }
  ]
}
```

---

### 3. `DELETE /api/v1/booking/request/<int:id_peticion>`
- **Purpose**: Cancels an active or pending booking request. Sets `estado = 'CANCELADA'`, sets the associated `Evento.activo = False`, and frees up the classroom slot.
- **Permissions**: Restricted to the owner (`id_usuario`), global `COORDINADOR`, or `ADMIN_PLANTEL` when the reservation belongs to a Salón in its assigned Plantel.
- **Responses**:
  - `200 OK`: Reservation cancelled and slot freed up.
  - `403 Forbidden`: User does not own the request and lacks admin rights.
  - `404 Not Found`: Request ID not found.
  - `409 Conflict`: Request is already in a terminal state and cannot be cancelled.
  - `503 Service Unavailable`: Catalog cannot safely validate `ADMIN_PLANTEL` scope.

---

### 4. `GET /api/v1/schedule/grid`
- **Purpose**: Returns active confirmed reservations: an active `Evento` associated with an `APROBADA` or `APARTADA` request. Pending requests are kept in history but do not appear as confirmed public occupancy.
- **Query Parameters**:
  - `id_salon`: Filter by room ID.
  - `id_programa`: Filter by academic program ID.
  - `fecha` / `fecha_reserva`: Filter by specific date (`YYYY-MM-DD`).
  - `id_plantel`: Filter by campus ID.
- **Response** (`200 OK`):
```json
{
  "total": 1,
  "grid": [
    {
      "id_peticion": 1,
      "id_salon": 101,
      "fecha_reserva": "2026-09-15",
      "hora_inicio": "08:00:00",
      "hora_fin": "10:00:00",
      "estado": "APROBADA",
      "materia_nombre": "Base de Datos Avanzada",
      "id_usuario": 10,
      "prioridad_calculada": 90,
      "nombre_tipo_evento": "Clase Curricular"
    }
  ]
}
```

---

## Quick Start & Testing

### 1. Manual Testing (`pruebas_manuales.http`)
Open `booking/pruebas_manuales.http` in VS Code with the **REST Client** extension or import into Postman. It includes a complete workflow:
1. Log in via IAM (`http://localhost:5001/api/v1/auth/login`) to acquire JWT tokens for Docente, Alumno, Encargado, and Admin.
2. Submit a high-priority reservation (Docente, $P=90$).
3. Attempt a overlapping reservation with lower priority (Alumno, $P=20$) $\rightarrow$ Expect `409 Conflict`.
4. High-priority displacement testing.
5. History query and deletion/cancellation workflows.
6. Public schedule grid matrix lookup.

### 2. Running Automated Tests

```powershell
# From project root
.\booking\venv\Scripts\python.exe -m pytest booking/tests/
```

---

## Architecture & How It Works

1. **Authentication**: Handled via JWT tokens issued by IAM. The `@login_required` decorator validates signatures with `JWT_SECRET_KEY` and injects `current_user_payload` into route handlers.
2. **Inter-Service Communication**: Validates classroom existence and capacity via `GET /api/v1/salones/<id_salon>`, and resolves all current or inactive Salones for `ADMIN_PLANTEL` scope through `GET /api/v1/salones?active_only=false&id_plantel=<id>`.
3. **Database Schema**: All tables reside in PostgreSQL schema `reservas`. On service startup (`init_db`), schemas are created and default `tipo_evento` priority weights are seeded automatically.
4. **Concurrency & Atomicity**: Database transactions perform pessimistic row-level locking (`SELECT ... FOR UPDATE`) over matching room and date rows to avoid simultaneous double booking.

---

## Contributing

Please follow the repository's coding standards, maintain docstrings, and update test suites when adding new endpoints or updating models. Submit pull requests against the `development` branch.

---

## License

This microservice is part of the *Sistema de gestión de horarios* project and is licensed under the same terms as the top-level repository.
