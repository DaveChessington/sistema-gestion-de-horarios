# Sistema de gestión de horarios UDL (Version 1.0 - MVP)

## Objetivo General del Proyecto

El objetivo general de este proyecto es proporcionar una plataforma centralizada y modular para administrar la asignación de espacios físicos (salones, auditorios, laboratorios) y recursos institucionales (equipos, programas educativos) dentro de la universidad. El sistema busca optimizar la planificación académica y administrativa mediante la resolución y prevención automatizada de conflictos de horarios (colisiones), garantizando la transparencia y eficiencia en el uso de las instalaciones para coordinadores, administradores de plantel, docentes y alumnos.

## Arquitectura

MVP modular con Flask, Jinja2 y PostgreSQL:

- `iam`: autenticación, JWT, roles y usuarios.
- `catalog`: planteles, salones, equipos y programas.
- `booking`: peticiones, reservas confirmadas, colisiones y horarios.
- `schedule`: vistas públicas y administrativas (Frontend).

## Ejecución

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
