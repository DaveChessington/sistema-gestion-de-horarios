# Sistema de gestión de horarios UDL (Version 1.0 - MVP)

## Objetivo General del Proyecto

Sistema web modular para consultar la ocupación de espacios académicos y administrar usuarios, infraestructura, inventario tecnológico y reservas. El MVP utiliza Flask, Jinja2, PostgreSQL y comunicación HTTP REST.

El objetivo general de este proyecto es proporcionar una plataforma centralizada y modular para administrar la asignación de espacios físicos (salones, auditorios, laboratorios) y recursos institucionales (equipos, programas educativos) dentro de la universidad. El sistema busca optimizar la planificación académica y administrativa mediante la resolución y prevención automatizada de conflictos de horarios (colisiones), garantizando la transparencia y eficiencia en el uso de las instalaciones para coordinadores, administradores de plantel, docentes y alumnos.

> Este README describe la implementación presente al 17 de agosto de 2026. Los documentos anteriores que presentan pantallas como *mockups* o proponen RabbitMQ, Redis, SSE, FastAPI, carga Excel/CSV y notificaciones externas corresponden a etapas previas y no a la solución vigente.

## Objetivo, problema y alcance

El proyecto centraliza la autenticación institucional, los catálogos de espacios y recursos, la consulta de horarios y el ciclo de vida de las reservas. Busca reducir la dispersión de información y los conflictos de asignación mediante controles de capacidad, alcance por plantel, detección de solapamientos y reglas de prioridad/FIFO.

Incluye:

- inicio/cierre de sesión y autorización por roles;
- consulta pública de horarios por plantel, salón, programa y fecha;
- altas, edición y baja lógica de planteles, salones, equipos, programas y usuarios;
- asociación de programas con equipos;
- alta, historial, reprogramación y cancelación de reservas;
- bloques institucionales de 50 minutos y resolución síncrona de colisiones;
- panel administrativo con métricas agregadas y manejo de resultados parciales.

No incluye brokers, SSE/WebSockets, *polling* periódico, importación Excel/CSV, notificaciones externas, OAuth, reubicación automática ni cambios de estado programados.

## Requisitos y dependencias

- Python compatible con las dependencias. La suite vigente se ejecutó con Python 3.14.3; una fuente de diseño menciona Python 3.11+, sin fijar una versión única de producción.
- Docker y Docker Compose.
- Entorno virtual `.venv` o equivalente.
- Puertos 5001–5004 y 5432 disponibles, salvo configuración distinta.
- Navegador moderno con JavaScript.

Las dependencias exactas están en los `requirements.txt` de cada módulo y `iam/requirements-security.txt`. Existen versiones diferentes de pytest declaradas; el entorno raíz verificado utiliza pytest 7.4.3.

## Instalación, configuración y puesta en marcha

1. Cree el entorno a partir del ejemplo y reemplace secretos y credenciales:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Configure `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `DB_NAME` y `JWT_SECRET_KEY`. No use los valores de ejemplo en producción.

3. Instale dependencias en el entorno virtual:

   ```powershell
   .venv\Scripts\python.exe -m pip install -r iam\requirements.txt
   .venv\Scripts\python.exe -m pip install -r iam\requirements-security.txt
   .venv\Scripts\python.exe -m pip install -r catalog\requirements.txt
   .venv\Scripts\python.exe -m pip install -r booking\requirements.txt
   .venv\Scripts\python.exe -m pip install -r schedule\requirements.txt
   ```

4. Inicie persistencia y API:

   ```powershell
   docker compose up -d --build postgres_db iam catalog booking
   ```

5. Si no hay administrador inicial, créelo desde IAM (el comando solicita contraseña):

   ```powershell
   docker compose exec iam flask --app run:app create-admin --correo admin@udl.edu.mx
   ```

6. Inicie la interfaz:

   ```powershell
   .venv\Scripts\python.exe schedule\run.py
   ```

Abra `http://127.0.0.1:5004/login`. Para impedir que Schedule abra el navegador:

```powershell
$env:SCHEDULE_OPEN_BROWSER="false"
.venv\Scripts\python.exe schedule\run.py
```

Las integraciones admiten `IAM_API_BASE_URL`, `IAM_REQUEST_TIMEOUT`, `CATALOG_API_BASE_URL`, `CATALOG_REQUEST_TIMEOUT`, `BOOKING_API_BASE_URL`, `BOOKING_REQUEST_TIMEOUT` y `SCHEDULE_SECRET_KEY`.

## Datos demostrativos opcionales

Con los servicios activos y una cuenta `COORDINADOR`, el *seed* idempotente crea solo registros faltantes:

```powershell
$env:SEED_ADMIN_EMAIL="coordinador@udl.edu.mx"
$env:SEED_ADMIN_PASSWORD="contraseña-real-del-coordinador"
.venv\Scripts\python.exe scripts\seed_mvp.py
```

Las credenciales y datos de producción son **No especificado en las fuentes proporcionadas**.

## Ejecución y uso

- Ingrese correo y contraseña institucionales en `/login`.
- `COORDINADOR` y `ADMIN_PLANTEL` acceden al panel administrativo.
- `DOCENTE` y `ALUMNO` acceden a la consulta pública.
- En Horarios, seleccione filtros y pulse **Consultar**; la cuadrícula se actualiza con Fetch/AJAX.
- En administración, use el menú de Planteles, Salones, Equipos, Programas, Usuarios u Horarios. Las acciones dependen del rol y plantel.

El manual completo y la evidencia están en [docs/DOCUMENTACION_OFICIAL.md](docs/DOCUMENTACION_OFICIAL.md).

## Estructura relevante

```text
.
├── iam/          # identidad y acceso
├── catalog/      # catálogos e inventario
├── booking/      # reservas y horarios
├── schedule/     # interfaz, plantillas, JS y clientes HTTP
├── scripts/      # seeding y orquestador de pruebas
├── docs/         # fuentes y documentación oficial
├── compose.yaml
├── .env.example
└── pytest.ini
```

## Pruebas

```powershell
.venv\Scripts\python.exe scripts\test_all.py
```

Última ejecución verificada: **17 de agosto de 2026; 279/279 casos aprobados** (IAM 21, Catalog 12, Booking 25, Schedule 221). Hubo advertencias por `datetime.utcnow()` y por una dependencia circular al limpiar tablas de Booking; no hubo fallas.

## Consideraciones y restricciones

- `ADMIN_PLANTEL` opera en su plantel; `COORDINADOR` tiene alcance global.
- Las bajas son lógicas y preservan historia.
- El JWT queda en la sesión firmada `HttpOnly`; las API vuelven a autorizar.
- La disponibilidad depende de IAM, Catalog, Booking y PostgreSQL; las vistas manejan errores controlados o resultados parciales.
- No existe `LICENSE`, aunque README de módulos remiten a uno en la raíz.
- Respaldo, recuperación, despliegue productivo, SLA y monitoreo son **No especificado en las fuentes proporcionadas**.

## Arquitectura

MVP modular con Flask, Jinja2 y PostgreSQL:

- `iam`: autenticación, JWT, roles y usuarios.
- `catalog`: planteles, salones, equipos y programas.
- `booking`: peticiones, reservas confirmadas, colisiones y horarios.
- `schedule`: vistas públicas y administrativas (Frontend).

| Componente | Puerto | Responsabilidad |
|---|---:|---|
| `schedule` | 5004 | Interfaz Flask/Jinja2, sesión y clientes HTTP |
| `iam` | 5001 | Identidad, bcrypt, JWT, roles y usuarios |
| `catalog` | 5002 | Planteles, salones, equipos, programas y asociaciones |
| `booking` | 5003 | Peticiones, reservas, prioridades, colisiones e historial |
| `postgres_db` | 5432 | Persistencia relacional |

Schedule consume las API y no accede directamente a sus modelos o bases. Catalog usa el esquema PostgreSQL `catalogos` y Booking el esquema `reservas`. `compose.yaml` levanta PostgreSQL y las tres API; Schedule se ejecuta localmente según el procedimiento documentado.

## Ejecución con contenedores de docker

El proyecto está completamente dockerizado. Para construir y levantar todos los microservicios junto con la base de datos, ejecuta:

```bash
docker compose up -d --build
```

El frontend estará disponible en `http://localhost:5004/login`.

## Datos reproducibles de prueba

Primero debe existir una cuenta `COORDINADOR`. Después, con los servicios activos:

```powershell
$env:SEED_ADMIN_EMAIL="coordinador@udl.edu.mx"
$env:SEED_ADMIN_PASSWORD="contraseña-real-del-coordinador"
.venv\Scripts\python.exe scripts\seed_mvp.py
```

El script consume las APIs, puede ejecutarse varias veces y solo crea los
registros faltantes de Planteles, Salones, Programas, Equipos, Usuarios y
Reservas de demostración.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pip install -r iam\requirements-security.txt
.venv\Scripts\python.exe scripts\test_all.py
```

Cada suite se ejecuta en un proceso separado para mantener aislados los
paquetes internos `app` y `config` de cada servicio.

## Mantenimiento y contacto

Los documentos académicos identifican a Aldo David Amaro Chávez, Jorge Iván García Piña y David Adame Vázquez.