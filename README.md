# Sistema de gestión de horarios UDL

MVP modular con Flask, Jinja2 y PostgreSQL:

- `iam`: autenticación, JWT, roles y usuarios.
- `catalog`: planteles, salones, equipos y programas.
- `booking`: peticiones, reservas confirmadas, colisiones y horarios.
- `schedule`: vistas públicas y administrativas.

## Ejecución

```powershell
docker compose up -d --build postgres_db iam catalog booking
.venv\Scripts\python.exe schedule\run.py
```

El frontend se abre en `http://127.0.0.1:5004/login`.

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
