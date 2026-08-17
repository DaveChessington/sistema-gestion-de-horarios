# Frontend Flask/Jinja2

El módulo `schedule` contiene exclusivamente la capa de presentación del
sistema. Sirve las vistas con Flask/Jinja2 y conserva los recursos visuales en
`schedule/frontend`.

## Arquitectura del módulo

- `app/routes`: controladores HTTP separados entre vistas públicas,
  administrativas y redirecciones de compatibilidad heredadas.
- `app/clients`: adaptadores HTTP para IAM, Catalog y Booking; las rutas no
  acceden directamente a modelos ni bases de datos externas.
- `app/forms.py`: opciones y validaciones puras compartidas por los formularios
  administrativos.
- `app/permissions.py`: definición única de los roles públicos y
  administrativos reconocidos por la capa visual.
- `templates`: layouts y páginas Jinja2 organizadas por área pública y
  administrativa.
- `frontend`: hoja de estilos y comportamiento JavaScript progresivo de las
  vistas activas.
- `tests`: pruebas de rutas y de los contratos de los clientes HTTP.

Los prototipos HTML/JavaScript independientes usados durante la etapa visual ya
no forman parte del módulo. El único punto de entrada es la aplicación creada
por `schedule.app.create_app`, con `/login` como destino inicial.

La autenticación y la gestión de Usuarios se integran con IAM; las vistas de
Planteles, Salones, Equipos y Programas se integran con Catalog mediante
clientes HTTP propios de la capa de presentación. `schedule` no importa modelos
ni accede directamente a bases de datos de otros módulos. Las consultas pública
y administrativa de horarios obtienen la cuadrícula real de Booking; únicamente
el resumen administrativo conserva datos de muestra.

## Ejecución local

### Con Docker (Recomendado)

Desde la raíz del repositorio, puedes construir y levantar el contenedor del frontend junto con el resto de los microservicios usando Docker Compose:

```bash
docker compose up -d --build schedule
```

El frontend quedará disponible en `http://localhost:5004` y se comunicará automáticamente con los contenedores de `iam`, `catalog` y `booking` a través de la red interna de Docker.

### Sin Docker (Script local)

Desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe schedule\run.py
```

El frontend queda disponible en `http://127.0.0.1:5004`.
IAM debe estar disponible en `http://127.0.0.1:5001` antes de iniciar sesión o
gestionar Usuarios, y Catalog en `http://127.0.0.1:5002` para gestionar los
catálogos y resolver los Planteles asignados a usuarios.
Booking debe estar disponible en `http://127.0.0.1:5003` para consultar la
ocupación pública y administrativa de horarios.
Al iniciar, `run.py` abre automáticamente `/login` en el navegador. Para
desactivar este comportamiento:

```powershell
$env:SCHEDULE_OPEN_BROWSER="false"
.venv\Scripts\python.exe schedule\run.py
```

Configuración opcional de la integración:

```powershell
$env:IAM_API_BASE_URL="http://127.0.0.1:5001/api/v1/auth"
$env:IAM_REQUEST_TIMEOUT="5"
$env:CATALOG_API_BASE_URL="http://127.0.0.1:5002/api/v1"
$env:CATALOG_REQUEST_TIMEOUT="5"
$env:BOOKING_API_BASE_URL="http://127.0.0.1:5003/api/v1"
$env:BOOKING_REQUEST_TIMEOUT="5"
$env:SCHEDULE_SECRET_KEY="cambia-esta-clave-en-cada-entorno"
```

## Rutas públicas

- `/`: redirección al acceso institucional.
- `/login`: acceso institucional validado por IAM.
- `/horarios`: consulta pública de horarios obtenida desde Booking.
- `/api/horarios`: proxy JSON usado por los filtros Fetch/AJAX del calendario.
- `/api/horarios/filtros`: opciones de Planteles, Salones y Programas obtenidas desde Catalog.
- `/logout`: cierre de la sesión del frontend mediante `POST`.

IAM determina las credenciales válidas. Los roles `COORDINADOR` y
`ADMIN_PLANTEL` se dirigen al área administrativa; `DOCENTE` y `ALUMNO`
continúan hacia la consulta pública.

Cuando `DOCENTE` o `ALUMNO` mantiene una sesión activa, la cabecera pública
reemplaza el acceso por la identidad de la cuenta y un cierre de sesión mediante
`POST /logout`. Después del login también informa una sola vez que el rol está
limitado a vistas públicas. Una sesión administrativa puede volver al panel o
cerrar sesión desde la misma cabecera.

## Rutas administrativas

- `/admin`: resumen.
- `/admin/planteles` y `/admin/planteles/nuevo`.
- `/admin/salones` y `/admin/salones/nuevo`.
- `/admin/equipos` y `/admin/equipos/nuevo`.
- `/admin/programas` y `/admin/programas/nuevo`.
- `/admin/usuarios` y `/admin/usuarios/nuevo`.
- `/admin/horarios`, `/admin/horarios/nuevo` y
  `/admin/horarios/historial`.
- `/admin/horarios/<id>/editar`: reprogramación protegida de una reserva.

Las rutas administrativas requieren una sesión creada después de un login
exitoso contra IAM. El JWT se conserva en la cookie de sesión firmada, marcada
como `HttpOnly`, y no se escribe en `localStorage` ni en `sessionStorage`.
Catalog y Booking validan nuevamente el JWT de IAM en las operaciones
protegidas; la sesión del frontend no reemplaza esa autorización.

Planteles, Salones, Equipos y Programas consultan sus registros reales desde
Catalog. Sus formularios de alta envían los campos definidos por el contrato
del servicio usando el JWT de la sesión. Salones obtiene los Planteles activos;
Equipos obtiene Planteles y Salones activos y permite al `COORDINADOR` mantener
inventario sin Salón, como admite el contrato actual. Para conservar el alcance
institucional, `ADMIN_PLANTEL` debe asociarlo a un Salón de su plantel. Programas calcula sus métricas visuales
usando las asociaciones incluidas en los Equipos. Una cuenta `ADMIN_PLANTEL`
solo puede seleccionar ubicaciones de su plantel asignado. La búsqueda, filtros,
métricas y paginación siguen ejecutándose en el navegador. Planteles ya
permite editar registros activos mediante `PUT /api/v1/planteles/<id>` y
desactivarlos lógicamente mediante `DELETE /api/v1/planteles/<id>`. Catalog
vuelve a validar el JWT y el alcance del Plantel antes de aplicar cada cambio;
la desactivación también alcanza sus Salones y Equipos dependientes. Salones
aplica el mismo patrón con `PUT` y `DELETE /api/v1/salones/<id>`, valida una
capacidad mayor a cero y exige un Plantel activo permitido. Su desactivación
lógica también deja inactivos los Equipos asociados.
Equipos permite editar mediante `PUT /api/v1/equipos/<id>` y desactivar mediante
`DELETE /api/v1/equipos/<id>` sin modificar sus asociaciones de programas. Las
acciones solo se muestran para registros activos dentro del alcance de la sesión.
Programas aplica el mismo ciclo de edición y desactivación lógica mediante
`PUT` y `DELETE /api/v1/programas/<id>`. Es un catálogo institucional global
disponible para ambos roles administrativos; modificar sus datos no altera las
asociaciones existentes con Equipos.
La ruta `/admin/programas/<id>/equipos` permite buscar, vincular y desvincular
equipos activos mediante los endpoints de software de Catalog. `COORDINADOR`
puede operar sobre todo el inventario; `ADMIN_PLANTEL` solo recibe y puede
modificar equipos ubicados en salones de su plantel. Los equipos sin salón se
reservan a roles globales y Catalog vuelve a comprobar esa regla.

Usuarios consulta el endpoint protegido de IAM y resuelve los nombres de
Plantel mediante Catalog. El registro solo se expone desde las rutas
administrativas de `schedule`; los datos se envían a IAM y la contraseña nunca
se repuebla, se incluye en JSON visual ni se conserva en almacenamiento del
navegador. IAM es responsable de generar y persistir su hash.

El endpoint `/register` de IAM exige autenticación y los roles `COORDINADOR` o
`ADMIN_PLANTEL`. `schedule` reenvía el JWT de la sesión administrativa.

Las consultas pública y administrativa de Horarios usan
`/api/v1/schedule/grid` mediante un proxy JSON del mismo origen. Los filtros de
Plantel, Salón, Programa y fecha actualizan la cuadrícula con Fetch/AJAX sin
recargar la página. Se conservan los turnos Matutino y Vespertino con bloques
visuales de 50 minutos. Los registros de Booking se ubican según su día y el
solapamiento entre sus horas de inicio y fin. La vista administrativa respeta el
Plantel asignado cuando la sesión corresponde a `ADMIN_PLANTEL`.

El formulario administrativo de nueva reserva obtiene Planteles, Salones y
Programas activos desde Catalog y envía `POST /api/v1/booking/request` con el JWT
de IAM conservado en la sesión del servidor. Solo ofrece los bloques
institucionales de 50 minutos y valida el alcance del Plantel y la capacidad del
Salón antes de delegar a Booking el cálculo de prioridad y la resolución de
colisiones.

El historial administrativo consume `GET /api/v1/booking/history` con el mismo
JWT y permite filtrar por estado, Salón, fecha y usuario. Booking limita a
`ADMIN_PLANTEL` mediante los Salones resueltos desde Catalog; Schedule conserva
la misma validación como defensa adicional y no muestra datos si el alcance no
puede verificarse. Las solicitudes activas o pendientes se pueden cancelar desde
el historial después de una confirmación visual. Schedule envía un `POST` local,
mantiene el JWT fuera del navegador y delega la operación `DELETE` y su
autorización definitiva a Booking. Las solicitudes vigentes también pueden
reprogramarse; Schedule precarga el formulario y delega en Booking la operación
atómica `PATCH`, incluyendo capacidad, prioridad y colisiones.

El resumen administrativo consulta Catalog, IAM y el historial autorizado de
Booking. Solo expone conteos agregados al navegador y aplica el alcance del
plantel como defensa adicional para `ADMIN_PLANTEL`. Si un servicio falla, los
demás conteos permanecen disponibles y la vista identifica la consulta parcial.
El antiguo almacenamiento `mock-data.js` ya no forma parte del módulo.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest schedule\tests
```
