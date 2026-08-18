"""
seed_db.py — Script para poblar la base de datos del Sistema de Gestión de Horarios.

Ejecutar desde la raíz del proyecto con el venv de cualquiera de los módulos:

    # Opción 1: con venv de iam
    $env:PYTHONPATH="."; .\\iam\\venv\\Scripts\\python.exe seed_db.py

    # Opción 2: con venv de catalog
    $env:PYTHONPATH="."; .\\catalog\\venv\\Scripts\\python.exe seed_db.py

Requiere que la base de datos PostgreSQL esté corriendo y que las tablas
ya hayan sido creadas (via flask db upgrade o al iniciar los servicios).

Variables de entorno (.env en la raíz del proyecto):
    DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Cargar variables de entorno desde .env
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:
    print("[WARN] python-dotenv no instalado — usando variables del sistema.")

# ---------------------------------------------------------------------------
# Dependencia de werkzeug (disponible en todos los venvs del proyecto)
# ---------------------------------------------------------------------------
from werkzeug.security import generate_password_hash


# ===========================================================================
# DATOS SEMILLA
# ===========================================================================

USUARIOS = [
    {
        "nombre": "Admin",
        "apellido": "Sistema",
        "correo": "admin@udl.edu.mx",
        "password": "password123",
        "rol": "COORDINADOR",
        "activo": True,
        "id_plantel_asignado": None,
    },
    {
        "nombre": "Encargado",
        "apellido": "Plantel Norte",
        "correo": "encargado@udl.edu.mx",
        "password": "password123",
        "rol": "ADMIN_PLANTEL",
        "activo": True,
        "id_plantel_asignado": 1,
    },
    {
        "nombre": "Docente",
        "apellido": "Lopez",
        "correo": "docente@udl.edu.mx",
        "password": "password123",
        "rol": "DOCENTE",
        "activo": True,
        "id_plantel_asignado": 1,
    },
    {
        "nombre": "Alumno",
        "apellido": "Garcia",
        "correo": "alumno@udl.edu.mx",
        "password": "password123",
        "rol": "ALUMNO",
        "activo": True,
        "id_plantel_asignado": 1,
    },
]

PLANTELES = [
    {"nombre": "Plantel Norte",  "direccion": "Av. Universidad 123, Guadalajara", "activo": True},
    {"nombre": "Plantel Sur",    "direccion": "Blvd. Tecnologico 456, Zapopan",   "activo": True},
    {"nombre": "Plantel Centro", "direccion": "Calle Reforma 789, Guadalajara",   "activo": True},
]

SALONES = [
    # Plantel Norte
    {"numero": "A-101", "descripcion": "Aula principal norte",    "capacidad": 40, "plantel": "Plantel Norte", "activo": True},
    {"numero": "A-102", "descripcion": "Laboratorio de computo",  "capacidad": 30, "plantel": "Plantel Norte", "activo": True},
    {"numero": "A-103", "descripcion": "Aula multimedia",         "capacidad": 25, "plantel": "Plantel Norte", "activo": True},
    # Plantel Sur
    {"numero": "B-201", "descripcion": "Aula principal sur",      "capacidad": 35, "plantel": "Plantel Sur",   "activo": True},
    {"numero": "B-202", "descripcion": "Sala de conferencias",    "capacidad": 50, "plantel": "Plantel Sur",   "activo": True},
    # Plantel Centro
    {"numero": "C-301", "descripcion": "Aula teorica",            "capacidad": 45, "plantel": "Plantel Centro","activo": True},
]

PROGRAMAS = [
    {"nombre": "Microsoft Office",   "descripcion": "Suite ofimatica",                  "activo": True},
    {"nombre": "AutoCAD",            "descripcion": "Diseno asistido por computadora",   "activo": True},
    {"nombre": "Python 3.12",        "descripcion": "Interprete de Python",              "activo": True},
    {"nombre": "Visual Studio Code", "descripcion": "Editor de codigo fuente",           "activo": True},
    {"nombre": "MySQL Workbench",    "descripcion": "Cliente grafico para MySQL",        "activo": True},
    {"nombre": "MATLAB",             "descripcion": "Computacion numerica",              "activo": True},
]

EQUIPOS = [
    # Laboratorio A-102
    {"numero": "PC-A102-01", "descripcion": "Computadora 1 - Lab A-102",    "activo": True, "salon": "A-102"},
    {"numero": "PC-A102-02", "descripcion": "Computadora 2 - Lab A-102",    "activo": True, "salon": "A-102"},
    {"numero": "PC-A102-03", "descripcion": "Computadora 3 - Lab A-102",    "activo": True, "salon": "A-102"},
    # Aula multimedia A-103
    {"numero": "PROY-A103",  "descripcion": "Proyector principal A-103",    "activo": True, "salon": "A-103"},
    # Sala de conferencias B-202
    {"numero": "PC-B202-01", "descripcion": "Equipo de presentacion B-202", "activo": True, "salon": "B-202"},
]

# Software asignado por equipo: {numero_equipo: [nombre_programa, ...]}
SOFTWARE_ASIGNACIONES = {
    "PC-A102-01": ["Python 3.12", "Visual Studio Code", "MySQL Workbench"],
    "PC-A102-02": ["Python 3.12", "Visual Studio Code"],
    "PC-A102-03": ["Microsoft Office", "Python 3.12"],
    "PROY-A103":  ["Microsoft Office"],
    "PC-B202-01": ["Microsoft Office", "AutoCAD"],
}

TIPOS_EVENTO = [
    {"id_tipo_evento": 1, "nombre": "Clase Curricular",           "peso_evento": 50, "descripcion": "Clase regular impartida por docente"},
    {"id_tipo_evento": 2, "nombre": "Evento Institucional",       "peso_evento": 40, "descripcion": "Evento organizado por direccion o administracion"},
    {"id_tipo_evento": 3, "nombre": "Conferencia / Taller",       "peso_evento": 30, "descripcion": "Conferencia, seminario o taller especial"},
    {"id_tipo_evento": 4, "nombre": "Sesion de Estudio (Grupal)", "peso_evento": 10, "descripcion": "Practicas o estudio grupal de alumnos"},
]


# ===========================================================================
# HELPERS
# ===========================================================================

def _exists(session, model, **kwargs):
    return session.query(model).filter_by(**kwargs).first() is not None


# ===========================================================================
# SEED IAM
# ===========================================================================

def seed_iam():
    """Inserta usuarios de prueba usando la app del módulo iam."""
    print("\n[IAM] Inicializando app...")

    # Agregar el directorio iam al path para importaciones relativas
    iam_dir = os.path.join(BASE_DIR, "iam")
    if iam_dir not in sys.path:
        sys.path.insert(0, iam_dir)

    from app import create_app
    from app.extensions import db
    from app.models.usuario import Usuario, RolUsuario

    app = create_app()

    rol_map = {r.value: r for r in RolUsuario}

    print("[IAM] Sembrando usuarios...")
    created = 0
    with app.app_context():
        for data in USUARIOS:
            if not _exists(db.session, Usuario, correo=data["correo"]):
                u = Usuario(
                    nombre=data["nombre"],
                    apellido=data["apellido"],
                    correo=data["correo"],
                    password_hash=generate_password_hash(data["password"]),
                    rol=rol_map[data["rol"]],
                    activo=data["activo"],
                    id_plantel_asignado=data["id_plantel_asignado"],
                )
                db.session.add(u)
                created += 1
                print(f"  [+] {data['correo']} ({data['rol']})")
            else:
                print(f"  [=] Ya existe: {data['correo']}")
        db.session.commit()
    print(f"  => {created} usuario(s) creado(s).")

    # Limpiar el path de iam para evitar conflictos con catalog/booking
    if iam_dir in sys.path:
        sys.path.remove(iam_dir)


# ===========================================================================
# SEED CATALOG
# ===========================================================================

def seed_catalog():
    """Inserta planteles, salones, equipos y programas usando la app del módulo catalog."""
    print("\n[CATALOG] Inicializando app...")

    catalog_dir = os.path.join(BASE_DIR, "catalog")
    if catalog_dir not in sys.path:
        sys.path.insert(0, catalog_dir)

    # Limpiar módulos cacheados del módulo anterior para evitar colisiones
    for key in list(sys.modules.keys()):
        if key.startswith("app.") or key == "app" or key == "config":
            del sys.modules[key]

    from catalog.app import create_app
    from catalog.app.extensions import db
    from catalog.app.models.plantel import Plantel
    from catalog.app.models.salon import Salon
    from catalog.app.models.equipo import Equipo
    from catalog.app.models.programa import Programa

    app = create_app()

    with app.app_context():
        print("[CATALOG] Sembrando planteles...")
        plantel_ids = {}
        for data in PLANTELES:
            existing = db.session.query(Plantel).filter_by(nombre=data["nombre"]).first()
            if not existing:
                p = Plantel(**data)
                db.session.add(p)
                db.session.flush()
                plantel_ids[data["nombre"]] = p.id
                print(f"  [+] Plantel: {data['nombre']} (id={p.id})")
            else:
                plantel_ids[data["nombre"]] = existing.id
                print(f"  [=] Ya existe: {data['nombre']} (id={existing.id})")
        db.session.commit()

        print("[CATALOG] Sembrando salones...")
        salon_ids = {}
        for data in SALONES:
            id_plantel_real = plantel_ids[data["plantel"]]
            existing = db.session.query(Salon).filter_by(
                numero=data["numero"], id_plantel=id_plantel_real
            ).first()
            if not existing:
                s = Salon(
                    numero=data["numero"],
                    descripcion=data["descripcion"],
                    capacidad=data["capacidad"],
                    id_plantel=id_plantel_real,
                    activo=data["activo"],
                )
                db.session.add(s)
                db.session.flush()
                salon_ids[data["numero"]] = s.id_salon
                print(f"  [+] Salon: {data['numero']} (id_salon={s.id_salon}, cap={data['capacidad']})")
            else:
                salon_ids[data["numero"]] = existing.id_salon
                print(f"  [=] Ya existe: {data['numero']} (id_salon={existing.id_salon})")
        db.session.commit()

        print("[CATALOG] Sembrando programas...")
        programa_ids = {}
        for data in PROGRAMAS:
            existing = db.session.query(Programa).filter_by(nombre=data["nombre"]).first()
            if not existing:
                prog = Programa(**data)
                db.session.add(prog)
                db.session.flush()
                programa_ids[data["nombre"]] = prog.id_programa
                print(f"  [+] Programa: {data['nombre']} (id={prog.id_programa})")
            else:
                programa_ids[data["nombre"]] = existing.id_programa
                print(f"  [=] Ya existe: {data['nombre']} (id={existing.id_programa})")
        db.session.commit()

        print("[CATALOG] Sembrando equipos...")
        equipo_map = {}
        for data in EQUIPOS:
            id_salon_real = salon_ids.get(data["salon"])
            if id_salon_real is None:
                print(f"  [!] Salon '{data['salon']}' no encontrado para equipo {data['numero']}")
                continue
            existing = db.session.query(Equipo).filter_by(numero=data["numero"]).first()
            if not existing:
                e = Equipo(
                    numero=data["numero"],
                    descripcion=data["descripcion"],
                    activo=data["activo"],
                    id_salon=id_salon_real,
                )
                db.session.add(e)
                db.session.flush()
                equipo_map[data["numero"]] = e
                print(f"  [+] Equipo: {data['numero']} (id_equipo={e.id_equipo})")
            else:
                equipo_map[data["numero"]] = existing
                print(f"  [=] Ya existe: {data['numero']} (id_equipo={existing.id_equipo})")
        db.session.commit()

        print("[CATALOG] Asignando software a equipos...")
        for numero_eq, nombres_prog in SOFTWARE_ASIGNACIONES.items():
            equipo = equipo_map.get(numero_eq)
            if not equipo:
                print(f"  [!] Equipo no encontrado: {numero_eq}")
                continue
            for nombre_prog in nombres_prog:
                prog_id = programa_ids.get(nombre_prog)
                if prog_id is None:
                    print(f"  [!] Programa no encontrado: {nombre_prog}")
                    continue
                prog = db.session.get(Programa, prog_id)
                if prog and prog not in equipo.programas:
                    equipo.programas.append(prog)
                    print(f"  [+] {numero_eq} <- {nombre_prog}")
                else:
                    print(f"  [=] Asignacion ya existe: {numero_eq} <- {nombre_prog}")
        db.session.commit()

    if catalog_dir in sys.path:
        sys.path.remove(catalog_dir)


# ===========================================================================
# SEED BOOKING
# ===========================================================================

def seed_booking():
    """Inserta tipos de evento en el esquema reservas usando la app del módulo booking."""
    print("\n[BOOKING] Inicializando app...")

    booking_dir = os.path.join(BASE_DIR, "booking")
    if booking_dir not in sys.path:
        sys.path.insert(0, booking_dir)

    for key in list(sys.modules.keys()):
        if key.startswith("app.") or key == "app" or key == "config":
            del sys.modules[key]

    from booking.app import create_app
    from booking.app.extensions import db
    from booking.app.models.tipo_evento import TipoEvento

    app = create_app()

    print("[BOOKING] Sembrando tipos de evento...")
    created = 0
    with app.app_context():
        for data in TIPOS_EVENTO:
            existing = db.session.get(TipoEvento, data["id_tipo_evento"])
            if not existing:
                t = TipoEvento(**data)
                db.session.add(t)
                created += 1
                print(f"  [+] TipoEvento: {data['nombre']} (peso={data['peso_evento']})")
            else:
                print(f"  [=] Ya existe: {data['nombre']}")
        db.session.commit()
    print(f"  => {created} tipo(s) de evento creado(s).")

    if booking_dir in sys.path:
        sys.path.remove(booking_dir)


# ===========================================================================
# MAIN
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  Sistema de Gestion de Horarios - Seed Script")
    print("=" * 60)

    seed_iam()
    seed_catalog()
    seed_booking()

    print("\n" + "=" * 60)
    print("  Seed completado correctamente.")
    print("=" * 60)
