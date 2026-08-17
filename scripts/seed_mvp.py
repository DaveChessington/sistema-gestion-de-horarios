"""Carga de demostración idempotente a través de las APIs del MVP.

No importa modelos ni escribe directamente en esquemas ajenos. Requiere los
servicios IAM, Catalog y Booking activos, además de una cuenta COORDINADOR.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PLANTELES = [
    {"nombre": "Plantel León", "direccion": "León, Guanajuato"},
    {"nombre": "Plantel Centro", "direccion": "Zona Centro, Guanajuato"},
]
SALONES = [
    {"numero": "A-101", "descripcion": "Aula de propósito general", "capacidad": 35, "plantel": "Plantel León"},
    {"numero": "LAB-201", "descripcion": "Laboratorio de cómputo", "capacidad": 30, "plantel": "Plantel León"},
    {"numero": "C-102", "descripcion": "Aula multimedia", "capacidad": 28, "plantel": "Plantel Centro"},
]
PROGRAMAS = [
    {"nombre": "Python", "descripcion": "Entorno académico de programación"},
    {"nombre": "PostgreSQL", "descripcion": "Motor de base de datos para prácticas"},
]
EQUIPOS = [
    {"numero": "EQ-SEED-001", "descripcion": "Estación docente", "salon": "LAB-201", "programas": ["Python", "PostgreSQL"]},
    {"numero": "EQ-SEED-002", "descripcion": "Proyector multimedia", "salon": "C-102", "programas": []},
]
USUARIOS = [
    {"nombre": "Adriana", "apellido": "Plantel", "correo": "admin.plantel.prueba@udl.edu.mx", "rol": "ADMIN_PLANTEL", "plantel": "Plantel León"},
    {"nombre": "Diego", "apellido": "Docente", "correo": "docente.prueba@udl.edu.mx", "rol": "DOCENTE", "plantel": "Plantel León"},
    {"nombre": "Alma", "apellido": "Alumna", "correo": "alumno.prueba@udl.edu.mx", "rol": "ALUMNO", "plantel": "Plantel León"},
]
RESERVAS = [
    {"salon": "A-101", "programa": "Python", "materia_nombre": "Programación", "fecha_reserva": "2026-09-07", "hora_inicio": "08:00", "hora_fin": "08:50", "id_tipo_evento": 1, "numero_alumnos": 25},
    {"salon": "LAB-201", "programa": "PostgreSQL", "materia_nombre": "Bases de Datos", "fecha_reserva": "2026-09-08", "hora_inicio": "10:00", "hora_fin": "10:50", "id_tipo_evento": 1, "numero_alumnos": 24},
    {"salon": "C-102", "programa": None, "materia_nombre": "Taller institucional", "fecha_reserva": "2026-09-09", "hora_inicio": "16:00", "hora_fin": "16:50", "id_tipo_evento": 3, "numero_alumnos": 20},
]


class SeedError(RuntimeError):
    """Fallo controlado al consumir uno de los servicios."""


@dataclass
class ApiClient:
    base_url: str
    token: str | None = None

    def request(self, method: str, path: str, payload=None):
        headers = {"Accept": "application/json"}
        body = None
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=10) as response:
                content = response.read().decode("utf-8")
        except HTTPError as error:
            content = error.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(content).get("error", content)
            except json.JSONDecodeError:
                detail = content
            raise SeedError(f"{method} {path}: HTTP {error.code}: {detail}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise SeedError(f"{method} {path}: servicio no disponible: {error}") from error
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError as error:
            raise SeedError(f"{method} {path}: respuesta JSON inválida") from error


def by_value(records, field, value):
    """Búsqueda estable, sin distinguir mayúsculas, para idempotencia."""
    expected = str(value).strip().casefold()
    return next(
        (
            record for record in records
            if str(record.get(field, "")).strip().casefold() == expected
        ),
        None,
    )


def ensure_catalog(catalog: ApiClient):
    planteles = catalog.request("GET", "/planteles?active_only=false")
    for data in PLANTELES:
        if not by_value(planteles, "nombre", data["nombre"]):
            planteles.append(catalog.request("POST", "/planteles", data))
    plantel_ids = {item["nombre"]: item["id"] for item in planteles}

    salones = catalog.request("GET", "/salones?active_only=false")
    for source in SALONES:
        if not by_value(salones, "numero", source["numero"]):
            payload = {key: source[key] for key in ("numero", "descripcion", "capacidad")}
            payload["id_plantel"] = plantel_ids[source["plantel"]]
            salones.append(catalog.request("POST", "/salones", payload))
    salon_ids = {item["numero"]: item["id_salon"] for item in salones}

    programas = catalog.request("GET", "/programas?active_only=false")
    for data in PROGRAMAS:
        if not by_value(programas, "nombre", data["nombre"]):
            programas.append(catalog.request("POST", "/programas", data))
    programa_ids = {item["nombre"]: item["id_programa"] for item in programas}

    equipos = catalog.request("GET", "/equipos?active_only=false")
    for source in EQUIPOS:
        equipment = by_value(equipos, "numero", source["numero"])
        if not equipment:
            equipment = catalog.request("POST", "/equipos", {
                "numero": source["numero"],
                "descripcion": source["descripcion"],
                "id_salon": salon_ids[source["salon"]],
            })
            equipos.append(equipment)
        assigned = {
            item.get("id_programa")
            for item in equipment.get("programas", [])
        }
        for program_name in source["programas"]:
            program_id = programa_ids[program_name]
            if program_id not in assigned:
                catalog.request(
                    "POST",
                    f"/equipos/{equipment['id_equipo']}/software",
                    {"id_programa": program_id},
                )
    return plantel_ids, salon_ids, programa_ids


def ensure_users(iam: ApiClient, plantel_ids, seed_password):
    response = iam.request("GET", "/users")
    users = response.get("usuarios", [])
    for source in USUARIOS:
        if by_value(users, "correo", source["correo"]):
            continue
        payload = {
            key: source[key]
            for key in ("nombre", "apellido", "correo", "rol")
        }
        payload["password"] = seed_password
        payload["id_plantel_asignado"] = plantel_ids[source["plantel"]]
        created = iam.request("POST", "/register", payload)
        users.append(created.get("usuario", created))
    return users


def ensure_bookings(booking: ApiClient, salon_ids, programa_ids):
    history = booking.request("GET", "/booking/history").get("peticiones", [])
    for source in RESERVAS:
        salon_id = salon_ids[source["salon"]]
        duplicate = next((
            item for item in history
            if item.get("id_salon") == salon_id
            and item.get("fecha_reserva") == source["fecha_reserva"]
            and str(item.get("hora_inicio", ""))[:5] == source["hora_inicio"]
            and item.get("materia_nombre") == source["materia_nombre"]
        ), None)
        if duplicate:
            continue
        payload = {
            key: source[key]
            for key in (
                "materia_nombre", "fecha_reserva", "hora_inicio", "hora_fin",
                "id_tipo_evento", "numero_alumnos",
            )
        }
        payload["id_salon"] = salon_id
        payload["id_programa"] = (
            programa_ids[source["programa"]] if source["programa"] else None
        )
        result = booking.request("POST", "/booking/request", payload)
        history.append(result["peticion"])
    return history


def run(args):
    iam = ApiClient(args.iam_url)
    login = iam.request("POST", "/login", {
        "correo": args.admin_email,
        "password": args.admin_password,
    })
    token = login.get("token")
    if not token:
        raise SeedError("IAM no devolvió un token para la cuenta COORDINADOR")
    if str(login.get("usuario", {}).get("rol", "")).upper() != "COORDINADOR":
        raise SeedError("La cuenta indicada debe tener rol COORDINADOR")

    iam.token = token
    catalog = ApiClient(args.catalog_url, token)
    booking = ApiClient(args.booking_url, token)
    plantel_ids, salon_ids, programa_ids = ensure_catalog(catalog)
    users = ensure_users(iam, plantel_ids, args.seed_password)
    reservations = ensure_bookings(booking, salon_ids, programa_ids)
    print(
        "Seed MVP verificado: "
        f"{len(plantel_ids)} planteles, {len(salon_ids)} salones, "
        f"{len(programa_ids)} programas, {len(users)} usuarios y "
        f"{len(reservations)} solicitudes visibles."
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Carga idempotente del MVP mediante APIs")
    parser.add_argument("--iam-url", default=os.getenv("IAM_SEED_URL", "http://127.0.0.1:5001/api/v1/auth"))
    parser.add_argument("--catalog-url", default=os.getenv("CATALOG_SEED_URL", "http://127.0.0.1:5002/api/v1"))
    parser.add_argument("--booking-url", default=os.getenv("BOOKING_SEED_URL", "http://127.0.0.1:5003/api/v1"))
    parser.add_argument("--admin-email", default=os.getenv("SEED_ADMIN_EMAIL", "coordinador@udl.edu.mx"))
    parser.add_argument("--admin-password", default=os.getenv("SEED_ADMIN_PASSWORD"))
    parser.add_argument("--seed-password", default=os.getenv("SEED_USER_PASSWORD", "UdL-Pruebas-2026!"))
    args = parser.parse_args()
    if not args.admin_password:
        parser.error("define --admin-password o la variable SEED_ADMIN_PASSWORD")
    return args


if __name__ == "__main__":
    try:
        run(parse_args())
    except SeedError as error:
        raise SystemExit(f"ERROR: {error}") from error
