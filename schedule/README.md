# Frontend Flask/Jinja2

El módulo `schedule` contiene exclusivamente la capa de presentación del
sistema. Sirve las vistas con Flask/Jinja2 y conserva los recursos visuales en
`schedule/frontend`.

En esta etapa utiliza datos de muestra y no importa modelos, bases de datos ni
servicios de IAM, Catalog o Booking.

## Ejecución local

Desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe schedule\run.py
```

El frontend queda disponible en `http://127.0.0.1:5004`.
Al iniciar, `run.py` abre automáticamente `/login` en el navegador. Para
desactivar este comportamiento:

```powershell
$env:SCHEDULE_OPEN_BROWSER="false"
.venv\Scripts\python.exe schedule\run.py
```

## Rutas públicas

- `/`: redirección al acceso institucional.
- `/login`: acceso institucional con sesión mock.
- `/horarios`: consulta pública de horarios.

Credenciales locales de demostración:

- Correo: `admin@udl.edu.mx`
- Contraseña: `demo1234`

## Rutas administrativas

- `/admin`: resumen.
- `/admin/planteles` y `/admin/planteles/nuevo`.
- `/admin/salones` y `/admin/salones/nuevo`.
- `/admin/equipos` y `/admin/equipos/nuevo`.
- `/admin/programas` y `/admin/programas/nuevo`.
- `/admin/usuarios` y `/admin/usuarios/nuevo`.
- `/admin/horarios`.

Las rutas administrativas todavía no aplican autenticación real. El navegador
mantiene una sesión demostrativa en `sessionStorage`; esto es únicamente una
protección visual y no sustituye la autorización del servidor.

Planteles, Salones, Programas, Equipos y Usuarios ya permiten búsqueda, filtros,
paginación y altas mock. Salones reutiliza los Planteles activos como opciones
de ubicación; Equipos filtra los Salones activos por Plantel y conserva la
relación indirecta entre ambos. Usuarios conserva sus registros de muestra en
`localStorage`, pero nunca almacena las contraseñas capturadas ni modifica la
sesión demostrativa. Ninguno de estos registros se envía a los servicios del
proyecto.

El resumen administrativo calcula sus métricas directamente a partir de estos
catálogos mock y ofrece accesos navegables a Planteles, Salones, Equipos y
Programas. El bloque de estado representa totales locales, no actividad real ni
eventos de los servicios.

## Pruebas

```powershell
.venv\Scripts\python.exe -m pytest schedule\tests
```
